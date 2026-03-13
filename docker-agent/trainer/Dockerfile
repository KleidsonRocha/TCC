FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/root/.cache/huggingface \
    TRANSFORMERS_CACHE=/root/.cache/huggingface/transformers \
    HUGGINGFACE_HUB_CACHE=/root/.cache/huggingface/hub

WORKDIR /workspace

COPY trainer/requirements.txt /tmp/trainer-requirements.txt
RUN pip install --no-cache-dir -r /tmp/trainer-requirements.txt

CMD ["python", "trainer/train_pre_search_adapter.py", "--help"]
