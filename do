#!/bin/bash

set -e

SRC=$(dirname $0)

cd $SRC

ARG=${1:-""}


case $ARG in
    release)
        CURRENT_VERSION=$(cat pyproject.toml| grep version | cut -d '"' -f 2)
        echo Current version $CURRENT_VERSION

        NEW_VERSION=$(echo $CURRENT_VERSION | awk -F. '{print $1 "." $2+1 "." $3}')
        echo New version $NEW_VERSION
        poetry version $NEW_VERSION

        git add -u pyproject.toml
        git commit -m "Release v$NEW_VERSION"
        git tag v$NEW_VERSION

        poetry build
        poetry publish -u $(pass show i/pypi | grep username | cut -d ' ' -f 2 | tr -d '\n') -p $(pass show i/pypi | head -n 1 | tr -d '\n')
        git log --pretty=format:"%cn: %s" v$CURRENT_VERSION...v$NEW_VERSION  | grep -v -e "Merge" | grep -v "Release"| awk '!x[$0]++' > changelog.md
        git push origin master --tags
        gh release create v$NEW_VERSION -F changelog.md
        rm changelog.md
        ;;

    check)
        black .
        isort tg/*.py
        ;;

    *)
        poetry run python3 main.py
        ;;
esac
