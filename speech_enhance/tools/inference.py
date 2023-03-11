import click
import toml
import pathlib
import urllib.request

from speech_enhance.audio_zen.utils import initialize_module


@click.command()
@click.option("-C", "--configuration", type=str, help="Config file.")
@click.option(
    "-M",
    "--model_checkpoint_path",
    type=click.Path(exists=True),
    help="The path of the model's checkpoint.",
)
@click.option(
    "-I",
    "--dataset_dir_list",
    type=click.Path(exists=True),
    help="delimited list input",
    multiple=True,
)
@click.option(
    "-O",
    "--output_dir",
    type=click.Path(),
    required=True,
    help="The path for saving enhanced speeches.",
)
def main(configuration, model_checkpoint_path, dataset_dir_list, output_dir):
    if not configuration:
        configuration = pathlib.Path(__file__).parent.parent / "config/inference.toml"
        print(f"Use default configuration: {configuration}")
    if not model_checkpoint_path:
        model_checkpoint_path = pathlib.Path.home().joinpath(".local/share/speech_enhance/best_model.tar")
        print(f"Use default model path: {model_checkpoint_path}")
        if not model_checkpoint_path.exists():
            url = "https://github.com/Enucatl/FullSubNet-plus/releases/download/0.0.1/best_model.tar"
            print(f"Download model from {url}")
            pathlib.Path(model_checkpoint_path.parent).mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, model_checkpoint_path)

    configuration = toml.load(configuration)
    if len(dataset_dir_list) > 0:
        print(
            f"use specified dataset_dir_list: {dataset_dir_list}, instead of in config"
        )
        configuration["dataset"]["args"]["dataset_dir_list"] = dataset_dir_list
    inferencer_class = initialize_module(
        configuration["inferencer"]["path"], initialize=False
    )
    inferencer = inferencer_class(configuration, model_checkpoint_path, output_dir)
    inferencer()


if __name__ == "__main__":
    main()
