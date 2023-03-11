# FullSubNet+

This repository repackages the official PyTorch implementation of **"[FullSubNet+: Channel Attention FullSubNet with Complex Spectrograms for Speech Enhancement](https://arxiv.org/abs/2203.12188)"**,  accepted by ICASSP 2022.

📜[[Full Paper](https://arxiv.org/abs/2203.12188)] ▶[[Demo](https://hit-thusz-rookiecj.github.io/fullsubnet-plus.github.io/)] 💿[[Checkpoint](https://drive.google.com/file/d/1UJSt1G0P_aXry-u79LLU_l9tCnNa2u7C/view)]

For easy installation and denoising. Requires CUDA GPU.
I only repackaged inference, contributions welcome for other parts of the original code.

## Install

```shell
pip install speech_enhance@https://github.com/Enucatl/FullSubNet-plus.git
```

## Quick Usage

```
speech_enhance_inference -I <directory_with_input_16000_frame_rate_wavs> -O <output_dir>
```

## Citation
If you find our work useful in your research, please consider citing:
```
@inproceedings{chen2022fullsubnet+,
  title={FullSubNet+: Channel Attention FullSubNet with Complex Spectrograms for Speech Enhancement},
  author={Chen, Jun and Wang, Zilin and Tuo, Deyi and Wu, Zhiyong and Kang, Shiyin and Meng, Helen},
  booktitle={ICASSP 2022-2022 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)},
  pages={7857--7861},
  year={2022},
  organization={IEEE}
}
```
