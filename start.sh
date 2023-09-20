/opt/homebrew/opt/redis/bin/redis-server /opt/homebrew/etc/redis.conf &
python3 frontend/frontend.py &
python3 checkout/checkout.py &
python3 delivery/delivery.py &