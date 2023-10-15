"""Test the Bcrypt package."""

from app.bcrypt.utils import check_hashed_password, hash_password

class TestUtils:
    def test_hash_password(self) -> None:
        p1 = 'first password'
        p2 = ' '
        p3 = '123123123'
        p4 = '@!#(%(@!$*'
        assert check_hashed_password(hash_password(p1), p1)
        assert check_hashed_password(hash_password(p2), p2)
        assert check_hashed_password(hash_password(p3), p3)
        assert check_hashed_password(hash_password(p4), p4)
