import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pytz
from description_generator import DescriptionGenerator
from github import Auth, ContentFile, Github, Repository
from pydantic import BaseModel

# --- Classes ---


class Project(BaseModel):
    repo_name: str
    readme_update_time: datetime = datetime(
        year=2001, month=3, day=22, tzinfo=pytz.timezone("UTC")
    )  # Definitely didnt update any repos before my birthday so why not
    description_generated: int = 0  # Defaults to false
    description: str = ""


class Identifier(BaseModel):
    title: str
    description: str = ""
    pubDate: str
    updatedDate: str
    heroImage: str = "/post_img.webp"
    badge: str | None = None
    tags: list[str] = []


# --- Setup ---

# using an access token
auth = Auth.Token(os.environ.get("PYGITHUB_TOKEN", sys.argv[1]))
g = Github(auth=auth)
conn = sqlite3.connect("readme.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

description_generator = DescriptionGenerator(
    os.environ.get("OPENAI_API_KEY", sys.argv[2])
)

filename_pattern = r"(?i)\((?!https?:|//)([^)]+\.(?:jpg|png|webp|jpeg|svg|hevc|gif))\)"

# --- Functions ---


def add_identifier(readme: str, identifier: Identifier) -> str:
    block = f"""---
title: "{identifier.title}"
description: "{identifier.description}"
pubDate: "{identifier.pubDate}"
heroImage: "{identifier.heroImage}"
tags: {str(identifier.tags).replace("'", '"')}
---

"""
    return block + readme


def get_project_record(repo: Repository) -> Project | None:
    cursor.execute("SELECT * FROM Projects WHERE repo_name = ?", (repo.name,))
    res = cursor.fetchone()
    return Project.model_validate(dict(res)) if res is not None else None


def upsert_record(project_record: Project | None, project_info: Project) -> None:
    if project_record is None:
        cursor.execute(
            """INSERT INTO Projects (
            repo_name,
            readme_update_time,
            description_generated,
            description,
            ) VALUES (?, ?, ?, ?)""",
            (
                project_info.repo_name,
                project_info.readme_update_time,
                project_info.description_generated,
                project_info.description,
            ),
        )
    else:
        cursor.execute(
            """UPDATE Projects SET
            readme_update_time = ?,
            description_generated = ?,
            description = ?
            WHERE repo_name = ?""",
            (
                project_info.readme_update_time,
                project_info.description_generated,
                project_info.description,
                project_info.repo_name,
            ),
        )
    conn.commit()


def get_readme_date(readme: ContentFile.ContentFile, repo: Repository) -> datetime:
    readme_path = readme.path
    commits = repo.get_commits(path=readme_path)
    last_updated_commit = commits[0]  # most recent commit
    return last_updated_commit.commit.author.date


def main() -> None:
    for repo in g.get_user().get_repos():
        if not repo.private and (repo.owner.login == "Stephen-Hallett"):
            try:
                project_record = get_project_record(repo)
                project_info = Project(repo_name=repo.name)

                readme = repo.get_readme()

                # If haven't exited from try-except then get and update date
                date = get_readme_date(readme, repo)
                project_info.readme_update_time = date

                # Get contents and replace file references with public urls
                readme_contents = readme.decoded_content.decode("utf-8")
                all_files = re.findall(filename_pattern, readme_contents)
                if all_files:
                    for file in all_files:
                        file_url = f"https://github.com/Stephen-Hallett/{repo.name}/raw/{repo.default_branch}/{file}"
                        readme_contents = readme_contents.replace(file, file_url)

                if (
                    (project_record is None)
                    or (not project_record.description_generated)
                    or (
                        project_info.readme_update_time
                        > project_record.readme_update_time
                    )
                ):
                    if project_record is None:
                        print(f"{repo.name} is a new repo! Generating description")
                    elif not project_record.description_generated:
                        print(
                            f"A description was never generated for {repo.name}. Generating one now!"
                        )
                    else:
                        f"The README for {repo.name} has changed since last time! Generating an updated description."
                    description = (
                        description_generator.generate(readme_contents)
                        if len(readme_contents.strip())
                        else ""
                    )
                    project_info.description = description
                    project_info.description_generated = 1
                else:
                    print(
                        f"The README for {repo.name} hasn't changed since last time - skipping description generation."
                    )
                    description = project_record.description

                identifier_block = Identifier(
                    title=repo.name,
                    description=description,
                    pubDate=repo.created_at.strftime("%b %d %Y"),
                    updatedDate=repo.updated_at.strftime("%b %d %Y"),
                    tags=list(repo.get_languages().keys()),
                    heroImage=f"https://github.com/Stephen-Hallett/{repo.name}/raw/{repo.default_branch}/{all_files[0]}"
                    if all_files
                    else "/post_img.webp",
                )
                identified = add_identifier(readme_contents, identifier_block)

                project_root = Path(__file__).resolve().parent.parent
                target_path = (
                    project_root
                    / "app"
                    / "src"
                    / "content"
                    / "projects"
                    / f"{identifier_block.title}.md"
                )
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with Path(target_path).open("w") as f:
                    f.write(identified)
            except Exception as e:
                print(e)
            upsert_record(project_record, project_info)
            print()

    # To close connections after use
    g.close()


if __name__ == "__main__":
    main()
