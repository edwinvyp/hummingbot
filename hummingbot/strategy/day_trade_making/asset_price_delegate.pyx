from decimal import Decimal


cdef class AssetPriceDelegate:
    
    def get_mid_price(self) -> Decimal:
        return self.c_get_mid_price()
    

    cdef object c_get_mid_price(self):
        raise NotImplementedError

    @property
    def ready(self) -> bool:
        raise NotImplementedError

