from melate_app_lab.packaging import build_command, build_info, get_dist_path


def test_build_command_contains_pyinstaller():
    command = build_command()

    assert "PyInstaller" in command
    assert "MelateApp" in command


def test_build_info_does_not_create_dist(tmp_path):
    import melate_app_lab.packaging
    original_get_dist_path = melate_app_lab.packaging.get_dist_path
    temp_dist = tmp_path / "dist" / "MelateApp"
    melate_app_lab.packaging.get_dist_path = lambda: temp_dist
    try:
        info = build_info()
        assert info["dist_path"] == str(temp_dist)
        assert not temp_dist.exists()
    finally:
        melate_app_lab.packaging.get_dist_path = original_get_dist_path

