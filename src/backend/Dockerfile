FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY src/backend/ ./

RUN mkdir -p instance

ENV DATABASE_URL=sqlite:///instance/invoice_app.db
ENV JWT_SECRET_KEY=your-secret-key-change-in-production
ENV SECRET_KEY=your-secret-key-change-in-production

EXPOSE 5001

CMD ["python3", "app.py"]
