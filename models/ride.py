
class Ride:
    def __init__(self, origin, destination, available_at, end_at, price, duration):
        self.origin = origin
        self.destination = destination
        self.available_at = available_at
        self.end_at = end_at
        self.price = price
        self.duration = duration
        
    def __str__(self):
        return f"{self.origin} - {self.destination}, {self.available_at}:{self.end_at}, p: {self.price}, d: {self.duration}"

    def __repr__(self):
        return f"{self.origin} - {self.destination}"