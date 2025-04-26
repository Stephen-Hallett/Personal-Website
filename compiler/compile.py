import os
import re
import sys
from pathlib import Path

from description_generator import DescriptionGenerator
from github import Auth, Github
from pydantic import BaseModel


class Identifier(BaseModel):
    title: str
    description: str = ""
    pubDate: str
    updatedDate: str
    heroImage: str = "/post_img.webp"
    badge: str | None = None
    tags: list[str] = []


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


# using an access token
auth = Auth.Token(os.environ.get("GITHUB_TOKEN", sys.argv[1]))
g = Github(auth=auth)

description_generator = DescriptionGenerator(
    os.environ.get("OPENAI_API_KEY", sys.argv[2])
)

identifier_block = {}

filename_pattern = r"(?i)\((?!https?:|//)([^)]+\.(?:jpg|png|webp|jpeg|svg|hevc|gif))\)"

for repo in g.get_user().get_repos():
    if not repo.private and (repo.owner.login == "Stephen-Hallett"):
        try:
            readme = repo.get_readme()
            readme_contents = readme.decoded_content.decode("utf-8")
            all_files = re.findall(filename_pattern, readme_contents)
            if all_files:
                for file in all_files:
                    file_url = f"https://github.com/Stephen-Hallett/{repo.name}/raw/{repo.default_branch}/{file}"
                    readme_contents = readme_contents.replace(file, file_url)

            identifier_block = Identifier(
                title=repo.name,
                description=description_generator.generate(readme_contents)
                if len(readme_contents.strip())
                else "",
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
            with Path(target_path).open("w") as f:
                f.write(identified)
        except Exception as e:
            print(e)
        print()

# To close connections after use
g.close()
