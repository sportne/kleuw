import json

from kleuw.cli import main


def test_init_with_files_populates_list(tmp_path):
    project_file = tmp_path / "project.json"
    file1 = tmp_path / "file1.txt"
    file1.write_text("content1")
    file2 = tmp_path / "file2.txt"
    file2.write_text("content2")

    exit_code = main(["init", str(project_file), str(file1), str(file2)])
    assert exit_code == 0
    assert project_file.exists()

    with project_file.open() as f:
        data = json.load(f)
    assert data["version"] == 1
    assert len(data["files"]) == 2
    paths = [f["path"] for f in data["files"]]
    assert str(file1) in paths
    assert str(file2) in paths


def test_create_link_auto_adds_files(tmp_path):
    project_file = tmp_path / "project.json"
    main(["init", str(project_file)])

    file1 = tmp_path / "file1.txt"
    file1.write_text("content1\nline2")
    file2 = tmp_path / "file2.txt"
    file2.write_text("content2\nline2")

    exit_code = main(
        [
            "create-link",
            str(project_file),
            "--src",
            str(file1),
            "--dst",
            str(file2),
            "--type",
            "refers_to",
        ]
    )
    assert exit_code == 0

    with project_file.open() as f:
        data = json.load(f)

    assert len(data["files"]) == 2
    assert len(data["links"]) == 1
    link = data["links"][0]
    assert "file_id" in link["src"]
    assert "file_id" in link["dst"]

    file_ids = [f["id"] for f in data["files"]]
    assert link["src"]["file_id"] in file_ids
    assert link["dst"]["file_id"] in file_ids


def test_init_fails_if_file_missing(tmp_path):
    project_file = tmp_path / "project.json"
    missing_file = tmp_path / "missing.txt"
    # Do not create the file

    exit_code = main(["init", str(project_file), str(missing_file)])
    assert exit_code == 1
    assert not project_file.exists()


def test_init_fails_if_already_exists(tmp_path):
    project_file = tmp_path / "project.json"
    project_file.write_text("{}")

    exit_code = main(["init", str(project_file)])
    assert exit_code == 1


def test_format_target_variants():
    from kleuw.cli import _format_target

    # Test Missing 'end' line
    assert _format_target({"file_id": "f1", "lines": {"start": 10}}) == "f1:10"
    # Test path instead of file_id
    assert _format_target({"path": "p1", "lines": {"start": 5, "end": 10}}) == "p1:5-10"
    # Test no location
    assert _format_target({}) == "-"
    # wait location = str(target.get("file_id") or target.get("path") or "-")
    # If lines has no start, it just returns location.
    assert _format_target({"file_id": "f1"}) == "f1"


def test_evaluate_link_staleness_invalid_link():
    from kleuw.cli import _evaluate_link_staleness

    # Missing src/dst targets should raise ValueError in _link_from_mapping,
    # which _evaluate_link_staleness catches and returns False.
    assert _evaluate_link_staleness({}, file_lookup={}) is False


def test_format_hash_none():
    from kleuw.cli import _format_hash

    assert _format_hash(None) == "-"


def test_init_fails_if_save_project_fails(tmp_path, monkeypatch):
    from kleuw import cli

    project_file = tmp_path / "project_fail.json"

    def mock_save_project(*args, **kwargs):
        from kleuw.io import ProjectIOError

        raise ProjectIOError("Mock failure")

    monkeypatch.setattr(cli, "save_project", mock_save_project)

    exit_code = main(["init", str(project_file)])
    assert exit_code == 1


def test_init_fails_if_parent_dir_cannot_be_created(tmp_path, monkeypatch):
    from pathlib import Path

    project_file = tmp_path / "subdir" / "project.json"

    def mock_mkdir(self, *args, **kwargs):
        if "subdir" in str(self):
            raise OSError("Permission denied")
        return Path.mkdir(self, *args, **kwargs)

    # We need to be careful with patching mkdir as it's used by many things
    from kleuw import cli

    monkeypatch.setattr(cli.Path, "mkdir", mock_mkdir)

    exit_code = main(["init", str(project_file)])
    assert exit_code == 1
