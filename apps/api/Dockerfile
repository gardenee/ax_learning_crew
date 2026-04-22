FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# 세션 3 부터 쓰는 query embedding 모델을 이미지에 미리 내려받아 캐시한다.
# 이렇게 해두면 수강생 각자의 첫 API 호출이 1~2GB 다운로드 지연 없이 바로 응답한다.
# 이미지 build 시 네트워크 사용량이 늘고 이미지 크기가 ~1.5GB 커지지만,
# 수업 흐름에서 "첫 호출이 20초 이상 멈춤" 문제를 제거하는 게 더 중요하다.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('intfloat/multilingual-e5-large')"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
