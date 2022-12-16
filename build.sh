cd frontend
docker build -t taqueria-frontend .
docker image tag taqueria-frontend mreider/taqueria-frontend:latest
docker image push mreider/taqueria-frontend:latest
cd ../checkout
docker build -t taqueria-checkout .
docker image tag taqueria-checkout mreider/taqueria-checkout:latest
docker image push mreider/taqueria-checkout:latest
cd ../delivery
docker build -t taqueria-delivery .
docker image tag taqueria-delivery  mreider/taqueria-delivery:latest
docker image push mreider/taqueria-delivery:latest
cd ../generator
docker build -t taqueria-generator .
docker tag taqueria-generator mreider/taqueria-generator:latest
docker push mreider/taqueria-generator:latest
cd ../upgrader
docker build -t taqueria-upgrader .
docker tag taqueria-upgrader mreider/taqueria-upgrader:latest
docker push mreider/taqueria-upgrader:latest
cd ../redis
docker build -t taqueria-redis .
docker tag taqueria-redis mreider/taqueria-redis:latest
docker push mreider/taqueria-redis:latest
