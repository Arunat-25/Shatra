"""Валидация Pydantic-схем аутентификации."""

import uuid

import pytest
from pydantic import ValidationError

from backend.auth.constants import DISTRICTS
from backend.auth.schemas import (
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)


class TestRegisterRequest:
    def test_minimal_valid(self):
        req = RegisterRequest(username="user_1", password="pass1234")
        assert req.username == "user_1"
        assert req.district is None

    def test_full_profile(self):
        req = RegisterRequest(
            username="Иван",
            password="pass1234",
            first_name="Иван",
            last_name="Иванов",
            district="Чемал",
        )
        assert req.district == "Чемал"

    @pytest.mark.parametrize(
        "username",
        ["ab", "a" * 33, "user name", "user-name", "user@mail", ""],
    )
    def test_invalid_username(self, username):
        with pytest.raises(ValidationError):
            RegisterRequest(username=username, password="pass1234")

    @pytest.mark.parametrize(
        "username",
        ["abc", "User_42", "Ёлка_2024", "АлтайскийИгрок", "a" * 32],
    )
    def test_valid_usernames(self, username):
        req = RegisterRequest(username=username, password="pass1234")
        assert req.username == username

    @pytest.mark.parametrize("password", ["short", "1234567", ""])
    def test_password_too_short(self, password):
        with pytest.raises(ValidationError):
            RegisterRequest(username="validuser", password=password)

    @pytest.mark.parametrize("password", ["onlyletters", "12345678"])
    def test_password_missing_letter_or_digit(self, password):
        with pytest.raises(ValidationError):
            RegisterRequest(username="validuser", password=password)

    def test_password_with_cyrillic_letter_and_digit(self):
        req = RegisterRequest(username="validuser", password="пароль123")
        assert req.password == "пароль123"

    def test_invalid_district(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="validuser",
                password="pass1234",
                district="Москва",
            )

    def test_empty_string_district_allowed(self):
        """Пустая строка в JSON — отдельный случай от null."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="validuser",
                password="pass1234",
                district="",
            )


class TestLoginRequest:
    def test_valid(self):
        req = LoginRequest(username="player", password="x")
        assert req.username == "player"

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="ab", password="pass1234")


class TestProfileUpdateRequest:
    def test_partial_update(self):
        req = ProfileUpdateRequest(first_name="Новое")
        assert req.username is None
        assert req.last_name is None
        assert req.district is None

    def test_username_update_valid(self):
        req = ProfileUpdateRequest(username="НовыйНик")
        assert req.username == "НовыйНик"

    def test_invalid_username_rejected(self):
        with pytest.raises(ValidationError):
            ProfileUpdateRequest(username="ab")

    def test_clear_name_with_empty_string(self):
        req = ProfileUpdateRequest(first_name="")
        assert req.first_name == ""

    def test_invalid_district(self):
        with pytest.raises(ValidationError):
            ProfileUpdateRequest(district="Несуществующий")

    def test_all_districts_valid(self):
        for d in DISTRICTS:
            req = ProfileUpdateRequest(district=d)
            assert req.district == d
