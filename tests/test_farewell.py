from proj_template import farewell


def test_farewell() -> None:
    assert farewell("world") == "Goodbye, world!"
