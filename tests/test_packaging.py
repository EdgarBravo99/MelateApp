from melate_app_lab.packaging import build_command, build_info, get_dist_path


def test_build_command_contains_pyinstaller():
    command = build_command()

    assert "PyInstaller" in command
    assert "MelateApp" in command


def test_build_info_does_not_create_dist():
    info = build_info()

    assert info["dist_path"].endswith("dist\\MelateApp") or info["dist_path"].endswith("dist/MelateApp")
    assert not get_dist_path().exists()
