# Personal Portfolio

An Astro website which showcases all of my public projects, running services & my CV. This repository contains an astro website pulled from an astro [template](https://astro.build/themes/details/astrofy-personal-porfolio-website-template/) which has been modified for my requirements, and a compiler script which compiles the majority of the websites 'project' tab content based off of my public github repositories.

## Compiler

The compiler functionality makes the maintenance of the website significantly easier by automatically generating the project content based on my public repositories, updating every day only if there are changes. The compiler script has a few features which make it a huge time saver.

- Automatic project description generation using my [description generator package](https://github.com/Stephen-Hallett/Repo-Description-Generator)
- Conversion of all image file references in README's to public github URL's
- Utilise the first referenced image as the thumbnail photo
- Use github detected coding languages as the project tags
