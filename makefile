.PHONY: build start-api

build:
	@echo "Building the AWS SAM application..."
	sam build --use-container -ef env.json

start-api: build
	@echo "Starting the API Gateway locally..."
	sam local start-api -n env.json