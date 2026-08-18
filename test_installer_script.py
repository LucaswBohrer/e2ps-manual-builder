from pathlib import Path


INSTALLER_SCRIPT = Path(__file__).parent / "packaging" / "E2PSManualBuilder.iss"


def test_installer_closes_running_application_before_replacement() -> None:
    script = INSTALLER_SCRIPT.read_text(encoding="utf-8")

    assert "CloseApplications=yes" in script
    assert "CloseApplicationsFilter={#AppExeName}" in script
    assert "RestartApplications=yes" in script


def test_installer_keeps_the_existing_application_identity() -> None:
    script = INSTALLER_SCRIPT.read_text(encoding="utf-8")

    assert 'AppId={#AppId}' in script
    assert '#define AppExeName "E2PSManualBuilder.exe"' in script
