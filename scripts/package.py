"""Create a source-only GitHub upload ZIP using an explicit allowlist."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    '.gitignore', 'LICENSE', 'README.md', '.github/workflows/test.yml',
    'scripts/package.py', 'tests/test_library.py', 'docs/preview.png',
    'skills/local-material-library/SKILL.md',
    'skills/local-material-library/agents/openai.yaml',
    'skills/local-material-library/requirements.txt',
    'skills/local-material-library/references/workflow.md',
    'skills/local-material-library/scripts/run.py',
    'skills/local-material-library/scripts/library.py',
    'skills/local-material-library/scripts/demo.py',
    'skills/local-material-library/assets/ui/index.html',
    'skills/local-material-library/assets/ui/app.js',
    'skills/local-material-library/assets/ui/styles.css',
]


def main():
    target = ROOT / 'dist/local-material-library.zip'
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for relative in FILES:
            path = ROOT / relative
            if path.is_symlink():
                raise ValueError(f'Unexpected symlink: {relative}')
            archive.write(path, 'local-material-library/' + relative)
    print(target)


if __name__ == '__main__':
    main()
