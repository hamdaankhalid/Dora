# Dora The Pipeline Explorer

## Pipe Tools
- ADO pipeline related tools to solve common issues from dependency visualizations to querying

## Build & Run

1. Create a .env from .example-env and fill values

2. Build and run image 
    ```
    docker build -t dora . && docker run -p 5000:5000 -it dora
    ```
