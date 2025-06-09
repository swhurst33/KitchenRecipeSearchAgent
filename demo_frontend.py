#!/usr/bin/env python3
"""
Simple web frontend to demo the Kitchnsync Recipe Discovery Agent
"""

from flask import Flask, render_template, request, jsonify
import requests
import json
import threading
import time
import uvicorn
from agent import app as fastapi_app

# Create Flask app for demo frontend
demo_app = Flask(__name__)

@demo_app.route('/')
def index():
    return render_template('index.html')

@demo_app.route('/api/recipes', methods=['POST'])
def get_recipes():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Call the FastAPI agent
        response = requests.post(
            'http://localhost:5000/agent',
            json={'prompt': prompt},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return jsonify({'error': f'Agent error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# HTML template
template_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Kitchnsync Recipe Discovery Agent</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <style>
        .recipe-card { margin-bottom: 1.5rem; }
        .ingredient-list { max-height: 200px; overflow-y: auto; }
        .instruction-list { max-height: 250px; overflow-y: auto; }
        .loading { display: none; }
    </style>
</head>
<body>
    <div class="container my-5">
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <h1 class="text-center mb-4">🍳 Kitchnsync Recipe Discovery</h1>
                <p class="text-center text-muted">AI-powered recipe discovery from natural language prompts</p>
                
                <div class="card mb-4">
                    <div class="card-body">
                        <form id="recipeForm">
                            <div class="mb-3">
                                <label for="prompt" class="form-label">What would you like to cook?</label>
                                <input type="text" class="form-control" id="prompt" 
                                       placeholder="e.g., quick keto dinner, healthy breakfast, easy pasta..." required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">
                                <span class="search-text">Find Recipes</span>
                                <span class="loading">
                                    <span class="spinner-border spinner-border-sm me-2"></span>
                                    Searching recipes...
                                </span>
                            </button>
                        </form>
                    </div>
                </div>
                
                <div id="results"></div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('recipeForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const prompt = document.getElementById('prompt').value;
            const button = this.querySelector('button');
            const searchText = button.querySelector('.search-text');
            const loadingText = button.querySelector('.loading');
            const resultsDiv = document.getElementById('results');
            
            // Show loading state
            button.disabled = true;
            searchText.style.display = 'none';
            loadingText.style.display = 'inline';
            resultsDiv.innerHTML = '';
            
            try {
                const response = await fetch('/api/recipes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    displayRecipes(data.recipes, data.message);
                } else {
                    resultsDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                }
            } catch (error) {
                resultsDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
            } finally {
                // Reset button state
                button.disabled = false;
                searchText.style.display = 'inline';
                loadingText.style.display = 'none';
            }
        });
        
        function displayRecipes(recipes, message) {
            const resultsDiv = document.getElementById('results');
            
            if (!recipes || recipes.length === 0) {
                resultsDiv.innerHTML = '<div class="alert alert-warning">No recipes found. Try a different search.</div>';
                return;
            }
            
            let html = `<div class="alert alert-success">${message}</div>`;
            
            recipes.forEach(recipe => {
                html += `
                    <div class="card recipe-card">
                        <div class="row g-0">
                            ${recipe.image_url ? `
                                <div class="col-md-4">
                                    <img src="${recipe.image_url}" class="img-fluid rounded-start h-100" 
                                         style="object-fit: cover;" alt="${recipe.title}">
                                </div>
                            ` : ''}
                            <div class="${recipe.image_url ? 'col-md-8' : 'col-12'}">
                                <div class="card-body">
                                    <h5 class="card-title">${recipe.title}</h5>
                                    <p class="card-text">
                                        <small class="text-muted">
                                            <a href="${recipe.source_url}" target="_blank">View Original Recipe</a>
                                        </small>
                                    </p>
                                    
                                    ${recipe.macros ? `
                                        <div class="mb-3">
                                            <h6>Nutrition (per serving):</h6>
                                            <div class="row">
                                                ${recipe.macros.calories ? `<div class="col">📊 ${recipe.macros.calories} cal</div>` : ''}
                                                ${recipe.macros.protein ? `<div class="col">🥩 ${recipe.macros.protein}g protein</div>` : ''}
                                                ${recipe.macros.carbs ? `<div class="col">🍞 ${recipe.macros.carbs}g carbs</div>` : ''}
                                                ${recipe.macros.fat ? `<div class="col">🥑 ${recipe.macros.fat}g fat</div>` : ''}
                                            </div>
                                        </div>
                                    ` : ''}
                                    
                                    <div class="row">
                                        <div class="col-md-6">
                                            <h6>Ingredients (${recipe.ingredients.length}):</h6>
                                            <div class="ingredient-list small">
                                                <ul class="list-unstyled">
                                                    ${recipe.ingredients.map(ing => `
                                                        <li>• ${ing.text}</li>
                                                    `).join('')}
                                                </ul>
                                            </div>
                                        </div>
                                        <div class="col-md-6">
                                            <h6>Instructions (${recipe.instructions.length} steps):</h6>
                                            <div class="instruction-list small">
                                                <ol>
                                                    ${recipe.instructions.map(inst => `
                                                        <li>${inst}</li>
                                                    `).join('')}
                                                </ol>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            resultsDiv.innerHTML = html;
        }
    </script>
</body>
</html>'''

# Create templates directory and template
import os
os.makedirs('templates', exist_ok=True)
with open('templates/index.html', 'w') as f:
    f.write(template_html)

def start_fastapi_server():
    """Start FastAPI agent in background"""
    uvicorn.run(fastapi_app, host="0.0.0.0", port=5000, log_level="error")

def start_demo():
    """Start the demo with both servers"""
    print("Starting Kitchnsync Recipe Discovery Agent Demo...")
    
    # Start FastAPI agent in background thread
    fastapi_thread = threading.Thread(target=start_fastapi_server, daemon=True)
    fastapi_thread.start()
    
    # Wait for FastAPI to start
    time.sleep(3)
    
    print("FastAPI Agent started on port 5000")
    print("Demo frontend starting on port 3000...")
    print("\nDemo URLs:")
    print("- FastAPI Agent: http://localhost:5000")
    print("- Demo Frontend: http://localhost:3000")
    
    # Start Flask demo frontend
    demo_app.run(host="0.0.0.0", port=3000, debug=False)

if __name__ == "__main__":
    start_demo()