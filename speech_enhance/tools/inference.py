import click
import toml

from speech_enhance.audio_zen.utils import initialize_module


@click.command()
@click.option("-C", "--configuration", type=str, required=True, help="Config file.")
@click.option("-M", "--model_checkpoint_path", type=str, required=True, help="The path of the model's checkpoint.")
@click.option('-I', '--dataset_dir_list', type=click.Path(exists=True), help='delimited list input', multiple=True)
@click.option("-O", "--output_dir", type=click.Path(), required=True, help="The path for saving enhanced speeches.")
def main(configuration, model_checkpoint_path, dataset_dir_list, output_dir):
    configuration = toml.load(configuration)
    if len(dataset_dir_list) > 0:
        print(f"use specified dataset_dir_list: {dataset_dir_list}, instead of in config")
        configuration["dataset"]["args"]["dataset_dir_list"] = dataset_dir_list
    inferencer_class = initialize_module(configuration["inferencer"]["path"], initialize=False)
    inferencer = inferencer_class(
        configuration,
        model_checkpoint_path,
        output_dir
    )
    inferencer()


if __name__ == "__main__":
    main()
