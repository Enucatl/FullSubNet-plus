import matplotlib.pyplot as plt
import torch
from torch.cuda.amp import autocast
from tqdm import tqdm

from audio_zen.acoustics.feature import mag_phase, drop_band
from audio_zen.acoustics.mask import build_complex_ideal_ratio_mask, decompress_cIRM, build_ideal_ratio_mask
from audio_zen.trainer.base_trainer import BaseTrainer
from utils.logger import log

plt.switch_backend('agg')


class Trainer(BaseTrainer):
    def __init__(self, dist, rank, config, resume, only_validation, model, loss_function, optimizer, train_dataloader, validation_dataloader):
        super().__init__(dist, rank, config, resume, only_validation, model, loss_function, optimizer)
        self.train_dataloader = train_dataloader
        self.valid_dataloader = validation_dataloader

    def _train_epoch(self, epoch):

        loss_total = 0.0
        progress_bar = None

        if self.rank == 0:
            progress_bar = tqdm(total=len(self.train_dataloader), desc=f"Training")

        for noisy, clean in self.train_dataloader:
            self.optimizer.zero_grad()

            noisy = noisy.to(self.rank)
            clean = clean.to(self.rank)

            noisy_complex = self.torch_stft(noisy)
            clean_complex = self.torch_stft(clean)

            noisy_mag, _ = mag_phase(noisy_complex)
            clean_mag, _ = mag_phase(clean_complex)

            ground_truth_IRM = build_ideal_ratio_mask(noisy_mag, clean_mag)  # [B, F, T, 1]

            with autocast(enabled=self.use_amp):
                # [B, F, T] => [B, 1, F, T] => model => [B, 2, F, T] => [B, F, T, 2]
                noisy_mag = noisy_mag.unsqueeze(1)
                IRM = self.model(noisy_mag)
                IRM = IRM.permute(0, 2, 3, 1)
                loss = self.loss_function(ground_truth_IRM, IRM)

            self.scaler.scale(loss).backward()
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.clip_grad_norm_value)
            self.scaler.step(self.optimizer)
            self.scaler.update()

            loss_total += loss.item()

            if self.rank == 0:
                progress_bar.update(1)
                progress_bar.refresh()

        if self.rank == 0:
            log(f"[Train] Epoch {epoch}, Loss {loss_total / len(self.train_dataloader)}")
            self.writer.add_scalar(f"Loss/Train", loss_total / len(self.train_dataloader), epoch)

    @torch.no_grad()
    def _validation_epoch(self, epoch):
        progress_bar = None
        if self.rank == 0:
            progress_bar = tqdm(total=len(self.valid_dataloader), desc=f"Validation")

        visualization_n_samples = self.visualization_config["n_samples"]
        visualization_num_workers = self.visualization_config["num_workers"]
        visualization_metrics = self.visualization_config["metrics"]

        loss_total = 0.0
        loss_list = {"With_reverb": 0.0, "No_reverb": 0.0, }
        item_idx_list = {"With_reverb": 0, "No_reverb": 0, }
        noisy_y_list = {"With_reverb": [], "No_reverb": [], }
        clean_y_list = {"With_reverb": [], "No_reverb": [], }
        enhanced_y_list = {"With_reverb": [], "No_reverb": [], }
        validation_score_list = {"With_reverb": 0.0, "No_reverb": 0.0}

        # speech_type in ("with_reverb", "no_reverb")
        for i, (noisy, clean, name, speech_type) in enumerate(self.valid_dataloader):
            assert len(name) == 1, "The batch size for the validation stage must be one."
            name = name[0]
            speech_type = speech_type[0]

            noisy = noisy.to(self.rank)
            clean = clean.to(self.rank)

            noisy_complex = self.torch_stft(noisy)
            clean_complex = self.torch_stft(clean)

            noisy_mag, noisy_angle = mag_phase(noisy_complex)
            clean_mag, _ = mag_phase(clean_complex)

            IRM = build_ideal_ratio_mask(noisy_mag, clean_mag)  # [B, F, T, 1]

            noisy_mag = noisy_mag.unsqueeze(1)
            RM = self.model(noisy_mag)
            RM = RM.permute(0, 2, 3, 1)

            loss = self.loss_function(IRM, RM)

            RM = decompress_cIRM(RM)
            # print(RM.shape)
            # print(torch.cos(noisy_angle).shape)
            # print(noisy_mag.shape)
            # enhanced_real = cRM[..., 0] * noisy_complex.real - cRM[..., 1] * noisy_complex.imag
            # enhanced_imag = cRM[..., 1] * noisy_complex.real + cRM[..., 0] * noisy_complex.imag
            enhanced_real = RM[..., 0] * noisy_mag[0, ...] * torch.cos(noisy_angle)
            enhanced_imag = RM[..., 0] * noisy_mag[0, ...] * torch.sin(noisy_angle)

            enhanced_complex = torch.stack((enhanced_real, enhanced_imag), dim=-1)
            enhanced = self.torch_istft(enhanced_complex, length=noisy.size(-1))

            noisy = noisy.detach().squeeze(0).cpu().numpy()
            clean = clean.detach().squeeze(0).cpu().numpy()
            enhanced = enhanced.detach().squeeze(0).cpu().numpy()

            assert len(noisy) == len(clean) == len(enhanced)
            loss_total += loss

            # Separated loss
            loss_list[speech_type] += loss
            item_idx_list[speech_type] += 1

            if item_idx_list[speech_type] <= visualization_n_samples:
                self.spec_audio_visualization(noisy, enhanced, clean, name, epoch, mark=speech_type)

            noisy_y_list[speech_type].append(noisy)
            clean_y_list[speech_type].append(clean)
            enhanced_y_list[speech_type].append(enhanced)

            if self.rank == 0:
                progress_bar.update(1)

        log(f"[Test] Epoch {epoch}, Loss {loss_total / len(self.valid_dataloader)}")
        self.writer.add_scalar(f"Loss/Validation_Total", loss_total / len(self.valid_dataloader), epoch)

        for speech_type in ("With_reverb", "No_reverb"):
            log(f"[Test] Epoch {epoch}, {speech_type}, Loss {loss_list[speech_type] / len(self.valid_dataloader)}")
            self.writer.add_scalar(f"Loss/{speech_type}", loss_list[speech_type] / len(self.valid_dataloader), epoch)

            validation_score_list[speech_type] = self.metrics_visualization(
                noisy_y_list[speech_type], clean_y_list[speech_type], enhanced_y_list[speech_type],
                visualization_metrics, epoch, visualization_num_workers, mark=speech_type
            )

        return validation_score_list["No_reverb"]
