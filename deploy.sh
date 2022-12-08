kubectl create namespace taqueria
kubectl apply -f frontend/frontend.yaml -n taqueria
kubectl apply -f delivery/delivery.yaml -n taqueria
kubectl apply -f checkout/checkout.yaml -n taqueria
kubectl apply -f scheduler/scheduler.yaml -n taqueria
kubectl apply -f redis/redis.yaml -n taqueria
