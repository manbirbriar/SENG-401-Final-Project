from new_ui import Parameter, api_call


def test_api():
    parameter = Parameter(
        exposure=0,
        contrast=0,
        white_levels=0,
        highlights=0,
        shadows=0,
        black_levels=0
    )
    api_call('../../sample_images/R62_0323.jpeg', 'I want to improve the texture of the goose.', parameter)
