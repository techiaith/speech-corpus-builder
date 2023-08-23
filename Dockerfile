FROM techiaith/wav2vec2-inference-gpu

RUN python3 -m pip install --upgrade pip && \
python3 -m pip install -U yt-dlp pycld3