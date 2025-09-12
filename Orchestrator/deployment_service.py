#!/usr/bin/env python3
"""
KubeRAG Deployment Service
Handles deployment operations from the UI
"""

import os
import subprocess
import json
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="KubeRAG Deployment Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DeploymentConfig(BaseModel):
    llm: Dict[str, Any]
    vectorStore: Dict[str, Any]
    apiKeys: Dict[str, str]
    nodePort: int

class DeploymentStatus:
    def __init__(self):
        self.status = "inactive"
        self.message = ""
        self.configuration = ""
        self.endpoint = ""

deployment_status = DeploymentStatus()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "deployment-service"}

@app.get("/api/deployment/status")
async def get_deployment_status():
    """Check the current deployment status"""
    try:
        # Check if namespace exists
        result = subprocess.run(
            ["kubectl", "get", "namespace", "kuberag"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return {
                "status": "inactive",
                "message": "Namespace not found",
                "configuration": "",
                "endpoint": ""
            }
        
        # Check if pods are running
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", "kuberag", "-o", "json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            pods = json.loads(result.stdout)
            if pods.get("items"):
                running_pods = sum(1 for pod in pods["items"] 
                                 if pod["status"]["phase"] == "Running")
                total_pods = len(pods["items"])
                
                if running_pods == total_pods and total_pods > 0:
                    return {
                        "status": "running",
                        "message": f"All {total_pods} pods running",
                        "configuration": "KubeRAG with Qdrant",
                        "endpoint": "localhost:30000"
                    }
                elif running_pods > 0:
                    return {
                        "status": "pending",
                        "message": f"{running_pods}/{total_pods} pods running",
                        "configuration": "KubeRAG with Qdrant",
                        "endpoint": ""
                    }
                else:
                    return {
                        "status": "failed",
                        "message": "No pods running",
                        "configuration": "",
                        "endpoint": ""
                    }
        
        return {
            "status": "inactive",
            "message": "No deployment found",
            "configuration": "",
            "endpoint": ""
        }
        
    except Exception as e:
        logger.error(f"Error checking deployment status: {e}")
        return {
            "status": "error",
            "message": str(e),
            "configuration": "",
            "endpoint": ""
        }

@app.post("/api/deployment/deploy")
async def deploy_configuration(config: DeploymentConfig):
    """Deploy KubeRAG with the specified configuration"""
    try:
        logger.info(f"Starting deployment with config: {config.llm['provider']}, {config.vectorStore['type']}")
        
        # Namespace will be created by Helm with --create-namespace flag
        logger.info("Preparing deployment...")
        
        # Prepare secrets as part of values file instead of creating separately
        # This way Helm manages the secrets
        logger.info("Preparing secrets configuration...")
        
        # Create values file for Helm
        values = {
            "llm": {
                "provider": config.llm['provider'],
                "azureOpenai": {
                    "deployment": config.llm.get('model', 'gpt-4'),
                    "apiVersion": "2024-02-01",
                    "apiKey": config.apiKeys.get('AZURE_OPENAI_API_KEY', ''),
                    "endpoint": config.apiKeys.get('AZURE_OPENAI_ENDPOINT', '')
                }
            },
            "vectorStore": {
                "type": config.vectorStore['type'],
                "dimension": 384,  # Fixed for all-MiniLM-L6-v2
                "collectionName": "documents"
            },
            "embedding": {
                "model": "all-MiniLM-L6-v2"
            },
            "service": {
                "type": "NodePort",
                "agent": {
                    "nodePort": config.nodePort
                },
                "pipeline": {
                    "nodePort": config.nodePort + 1
                }
            }
        }
        
        # Write values to temporary file
        values_file = "/tmp/kuberag-values.yaml"
        with open(values_file, 'w') as f:
            yaml.dump(values, f)
        
        # Deploy with Helm
        logger.info("Deploying with Helm...")
        helm_chart_path = str(Path(__file__).parent.parent / "KubeRag")
        
        helm_cmd = [
            "helm", "upgrade", "--install", "kuberag",
            helm_chart_path,
            "-n", "kuberag",
            "--create-namespace",
            "-f", values_file
        ]
        
        result = subprocess.run(helm_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Helm deployment failed: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Helm deployment failed: {result.stderr}")
        
        logger.info("Deployment initiated successfully")
        
        # Update status
        deployment_status.status = "pending"
        deployment_status.message = "Deployment in progress"
        deployment_status.configuration = f"{config.llm['provider']} with {config.vectorStore['type']}"
        deployment_status.endpoint = f"localhost:{config.nodePort}"
        
        return {
            "status": "success",
            "message": "Deployment initiated successfully",
            "details": result.stdout
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/deployment/undeploy")
async def undeploy_configuration():
    """Undeploy KubeRAG"""
    try:
        logger.info("Starting undeployment...")
        
        # Uninstall Helm release
        result = subprocess.run(
            ["helm", "uninstall", "kuberag", "-n", "kuberag"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 and "not found" not in result.stderr:
            logger.error(f"Failed to uninstall Helm release: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Failed to uninstall: {result.stderr}")
        
        # Delete namespace
        result = subprocess.run(
            ["kubectl", "delete", "namespace", "kuberag"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 and "not found" not in result.stderr:
            logger.error(f"Failed to delete namespace: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Failed to delete namespace: {result.stderr}")
        
        # Update status
        deployment_status.status = "inactive"
        deployment_status.message = "Undeployed successfully"
        deployment_status.configuration = ""
        deployment_status.endpoint = ""
        
        return {
            "status": "success",
            "message": "KubeRAG undeployed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Undeployment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)