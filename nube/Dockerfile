FROM python:3.12-slim

WORKDIR /app

# numpy<2.0 va en su propia capa y antes que todo lo demás: netplotbrain usa
# APIs que NumPy 2.x eliminó, y si pip resolviera todo junto podría traer 2.x.
RUN pip install --no-cache-dir "numpy>=1.24,<2.0"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=7860
EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
