#!/bin/bash

# Quick start script for running Locust and Prometheus on separate servers
# This script helps you quickly deploy the services with proper configuration

set -e  # Exit on error

echo "=========================================="
echo "RAG App - Separate Server Deployment"
echo "=========================================="
echo ""

# Function to display menu
show_menu() {
    echo "What would you like to deploy?"
    echo ""
    echo "1) RAG Application (Main App + Qdrant)"
    echo "2) Prometheus (Monitoring Server)"
    echo "3) Locust (Load Testing Server)"
    echo "4) Stop RAG Application"
    echo "5) Stop Prometheus"
    echo "6) Stop Locust"
    echo "7) View RAG App logs"
    echo "8) View Prometheus logs"
    echo "9) View Locust logs"
    echo "0) Exit"
    echo ""
    read -p "Enter your choice [0-9]: " choice
}

# Function to deploy RAG app
deploy_rag_app() {
    echo ""
    echo "Deploying RAG Application..."
    docker-compose up -d
    echo ""
    echo "RAG Application deployed successfully!"
    echo "Access the app at: http://localhost:8000"
    echo "Metrics endpoint: http://localhost:8000/metrics"
    echo "Qdrant dashboard: http://localhost:6333/dashboard"
    echo ""
    read -p "Press Enter to continue..."
}

# Function to deploy Prometheus
deploy_prometheus() {
    echo ""
    read -p "Enter the RAG app server IP/hostname (e.g., 192.168.1.100): " rag_server
    read -p "Enter the RAG app port [8000]: " rag_port
    rag_port=${rag_port:-8000}
    
    # Check if prometheus.yml exists, if not use prometheus.remote.yml
    if [ ! -f "prometheus.yml" ]; then
        if [ -f "prometheus.remote.yml" ]; then
            cp prometheus.remote.yml prometheus.yml
            echo "Created prometheus.yml from prometheus.remote.yml"
        else
            echo "Error: Neither prometheus.yml nor prometheus.remote.yml found!"
            read -p "Press Enter to continue..."
            return 1
        fi
    fi
    
    # Update the target in prometheus.yml
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-rag-server-ip:8000/${rag_server}:${rag_port}/g" prometheus.yml
    else
        # Linux
        sed -i "s/your-rag-server-ip:8000/${rag_server}:${rag_port}/g" prometheus.yml
    fi
    
    echo ""
    echo "Deploying Prometheus..."
    docker-compose -f docker-compose.prometheus.yml up -d
    echo ""
    echo "Prometheus deployed successfully!"
    echo "Access Prometheus at: http://localhost:9090"
    echo "Check targets at: http://localhost:9090/targets"
    echo ""
    echo "Verify that the 'rag-api' target is UP (green)"
    echo ""
    read -p "Press Enter to continue..."
}

# Function to deploy Locust
deploy_locust() {
    echo ""
    read -p "Enter the RAG app server URL (e.g., http://192.168.1.100:8000): " rag_url
    
    # Export the environment variable
    export RAG_APP_HOST="$rag_url"
    
    echo ""
    echo "Deploying Locust..."
    echo "Using RAG_APP_HOST=$RAG_APP_HOST"
    docker-compose -f docker-compose.locust.yml up -d
    echo ""
    echo "Locust deployed successfully!"
    echo "Access Locust web UI at: http://localhost:8089"
    echo ""
    echo "To configure a load test:"
    echo "1. Open http://localhost:8089 in your browser"
    echo "2. Set number of users (e.g., 10-50)"
    echo "3. Set spawn rate (e.g., 1-5 users/sec)"
    echo "4. Click 'Start swarming'"
    echo ""
    read -p "Press Enter to continue..."
}

# Function to stop services
stop_service() {
    local service=$1
    local compose_file=$2
    
    echo ""
    echo "Stopping $service..."
    if [ -z "$compose_file" ]; then
        docker-compose down
    else
        docker-compose -f "$compose_file" down
    fi
    echo "$service stopped successfully!"
    echo ""
    read -p "Press Enter to continue..."
}

# Function to view logs
view_logs() {
    local service=$1
    local compose_file=$2
    
    echo ""
    echo "Viewing logs for $service (Press Ctrl+C to exit)..."
    echo ""
    sleep 2
    
    if [ -z "$compose_file" ]; then
        docker-compose logs -f
    else
        docker-compose -f "$compose_file" logs -f
    fi
}

# Main loop
while true; do
    clear
    show_menu
    
    case $choice in
        1)
            deploy_rag_app
            ;;
        2)
            deploy_prometheus
            ;;
        3)
            deploy_locust
            ;;
        4)
            stop_service "RAG Application" ""
            ;;
        5)
            stop_service "Prometheus" "docker-compose.prometheus.yml"
            ;;
        6)
            stop_service "Locust" "docker-compose.locust.yml"
            ;;
        7)
            view_logs "RAG Application" ""
            ;;
        8)
            view_logs "Prometheus" "docker-compose.prometheus.yml"
            ;;
        9)
            view_logs "Locust" "docker-compose.locust.yml"
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid option. Please try again."
            sleep 2
            ;;
    esac
done
