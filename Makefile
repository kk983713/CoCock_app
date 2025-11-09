# Makefile for CoCock_app

.PHONY: help
help:
	@echo "Makefile targets:"
	@echo "  deploy-cloud-run    Deploy the app to Cloud Run (requires gcloud CLI)"

# Cloud Run deploy helper
deploy-cloud-run:
	@echo "Usage: make deploy-cloud-run PROJECT_ID=<PROJECT_ID> [TAG=v0.2]"
	@if [ -z "$(PROJECT_ID)" ]; then echo "Set PROJECT_ID variable, e.g. make deploy-cloud-run PROJECT_ID=my-gcp-project"; exit 2; fi
	./scripts/deploy_cloud_run.sh $(PROJECT_ID) ${TAG:-v0.2}

# Local development helpers
.PHONY: migrate run run-local clean

migrate:
	python3 db.py

run:
	streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501

run-local:
	streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501

clean:
	rm -f streamlit.log nohup.out || true
