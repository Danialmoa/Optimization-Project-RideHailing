import h3

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
    
    def to_dict(self):
        return {
            'origin': self.origin,
            'destination': self.destination,
            'available_at': self.available_at,
            'end_at': self.end_at,
            'price': self.price,
            'duration': self.duration,
            'lat_origin': h3.cell_to_latlng(self.origin)[0],
            'lng_origin': h3.cell_to_latlng(self.origin)[1],
            'lat_destination': h3.cell_to_latlng(self.destination)[0],
            'lng_destination': h3.cell_to_latlng(self.destination)[1]
        }