#!/bin/bash

echo "=========================================="
echo "BiasLens Full Pipeline"
echo "=========================================="

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source biaslensvenv/bin/activate

# Install requirements if needed
echo "📦 Installing requirements..."
pip install -r req.txt

# Run ETL pipeline (scraping + clustering + fact extraction)
echo "🚀 Running ETL pipeline..."
python3 etl/pipeline_runner.py

# Check if pipeline succeeded
if [ $? -eq 0 ]; then
    echo "✅ ETL pipeline completed successfully"
else
    echo "❌ ETL pipeline failed"
    exit 1
fi

# Generate reports
echo "📝 Generating article reports..."
python3 generation/article_generator.py

# Launch Streamlit viewer
echo "🌐 Launching Streamlit viewer..."
streamlit run generation/streamlit_viewer.py