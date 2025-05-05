import os
import re
import sys
from datetime import datetime
from pathlib import Path

import polars as pl
import pytz
from description_generator import DescriptionGenerator
from github import Auth, ContentFile, Github, Repository
from pydantic import BaseModel

# --- Classes ---


class Project(BaseModel):
    repo_name: str
    readme_update_time: datetime = datetime(
        year=2001, month=3, day=22, tzinfo=pytz.timezone("UTC")
    )
    description_generated: bool = False
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

auth = Auth.Token(os.environ.get("PYGITHUB_TOKEN", sys.argv[1]))
g = Github(auth=auth)

CSV_PATH = "readme.csv"
if not Path(CSV_PATH).exists():
    pl.DataFrame(
        schema={
            "repo_name": pl.Utf8,
            "readme_update_time": pl.Datetime,
            "description_generated": pl.Boolean,
            "description": pl.Utf8,
        }
    ).write_csv(CSV_PATH)

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
updatedDate: "{identifier.updatedDate}"
heroImage: "{identifier.heroImage}"
tags: {str(identifier.tags).replace("'", '"')}
{'badge: "' + identifier.badge + '"' if identifier.badge is not None else '""'}
---

"""
    return block + readme


def load_projects_df() -> pl.DataFrame:
    return pl.read_csv(CSV_PATH, try_parse_dates=True)


def get_project_record(repo: Repository, df: pl.DataFrame) -> Project | None:
    ctx = pl.SQLContext(df=df)
    res = ctx.execute(f"""
        SELECT * FROM df
        WHERE repo_name = '{repo.name}'
        LIMIT 1
    """).collect()
    return Project.model_validate(res.to_dicts()[0]) if res.height > 0 else None


def upsert_record(
    df: pl.DataFrame, project_record: Project | None, project_info: Project
) -> pl.DataFrame:
    rows = df.to_dicts()
    if project_record is None:
        rows.append(project_info.model_dump())
    else:
        for i, row in enumerate(rows):
            if row["repo_name"] == project_info.repo_name:
                rows[i] = project_info.model_dump()
                break
    return pl.DataFrame(rows)


def get_readme_date(readme: ContentFile.ContentFile, repo: Repository) -> datetime:
    readme_path = readme.path
    commits = repo.get_commits(path=readme_path)
    return commits[0].commit.author.date


def get_update_badge(updated_at: datetime) -> str:
    days = (datetime.now(tz=pytz.timezone("UTC")) - updated_at).days
    if days == 0:
        return "Updated today"
    if days == 1:
        return "Updated yesterday"
    if days < 8:
        return f"Updated {days} days ago"
    return ""


# --- Main ---


def main() -> None:
    df = load_projects_df()
    for repo in g.get_user().get_repos():
        if not repo.private and repo.owner.login == "Stephen-Hallett":
            try:
                project_record = get_project_record(repo, df)
                project_info = Project(repo_name=repo.name)

                readme = repo.get_readme()
                date = get_readme_date(readme, repo)
                project_info.readme_update_time = date

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
                    project_info.description_generated = True
                    df = upsert_record(df, project_record, project_info)
                else:
                    print(
                        f"The README for {repo.name} hasn't changed since last time - skipping description generation."
                    )
                    description = project_record.description

                identifier_block = Identifier(
                    title=repo.name,
                    description=description,
                    pubDate=repo.created_at.strftime("%b %d %Y %H:%M"),
                    updatedDate=repo.updated_at.strftime("%b %d %Y %H:%M"),
                    tags=list(repo.get_languages().keys()),
                    heroImage=f"https://github.com/Stephen-Hallett/{repo.name}/raw/{repo.default_branch}/{all_files[0]}"
                    if all_files
                    else "/post_img.webp",
                    badge=get_update_badge(repo.updated_at),
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
                with target_path.open("w") as f:
                    f.write(identified)
            except Exception as e:
                print(e)
            print()
    df.write_csv(CSV_PATH)
    g.close()


if __name__ == "__main__":
    main()
