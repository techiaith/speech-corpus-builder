default: build

$(eval DEVICE = cpu)
#$(eval DEVICE = gpu)

config:
	$(eval MODEL_NAME = techiaith/wav2vec2-xlsr-ft-en-cy)
	$(eval MODEL_VERSION = 23.03)
	mkdir -p ${PWD}/data


build: config
	docker build --rm -t techiaith/speech-corpus-builder \
	--build-arg WAV2VEC2_MODEL_NAME=${MODEL_NAME} \
	--build-arg WAV2VEC2_MODEL_VERSION=${MODEL_VERSION} \
	.


run: config run-${DEVICE}


run-cpu:
	docker run --name speech-corpus-builder-${DEVICE} \
	--restart=always \
	-it \
	-v ${PWD}/data/:/data \
	-v ${PWD}/scripts/:/corpus-builder \
	techiaith/speech-corpus-builder


run-gpu:
	docker run --gpus all \
	--name speech-corpus-builder-${DEVICE} \
	--restart=always \
	-it \
	-v ${PWD}/data/:/data \
	-v ${PWD}/scripts/:/corpus-builder \
	techiaith/speech-corpus-builder


stop: config
	-docker stop speech-corpus-builder-${DEVICE}
	-docker rm speech-corpus-builder-${DEVICE}


clean: config stop
	-docker rmi techiaith/speech-corpus-builder
	
