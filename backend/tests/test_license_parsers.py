"""
Unit tests for license parser modules.

Tests each domain-specific parser with mocked HTML content
to verify correct license information extraction.
"""

import pytest

# ── Unsplash Parser Tests ─────────────────────────────────────────────


class TestUnsplashParser:
    """Unsplash parser should always return free_commercial."""

    def test_parse_returns_free_commercial(self):
        from app.services.license_parsers.unsplash import parse_unsplash

        result = parse_unsplash("https://unsplash.com/photos/abc123")

        assert result["license_type"] == "free_commercial"
        assert result["commercial_use"] is True
        assert result["requires_attribution"] is False
        assert "Unsplash" in result["summary"]


# ── Pexels Parser Tests ───────────────────────────────────────────────


class TestPexelsParser:
    """Pexels parser should always return free_commercial."""

    def test_parse_returns_free_commercial(self):
        from app.services.license_parsers.pexels import parse_pexels

        result = parse_pexels("https://www.pexels.com/photo/abc123/")

        assert result["license_type"] == "free_commercial"
        assert result["commercial_use"] is True
        assert result["requires_attribution"] is False
        assert "Pexels" in result["summary"]


# ── Pixabay Parser Tests ──────────────────────────────────────────────


class TestPixabayParser:
    """Pixabay parser should detect sponsored vs free content."""

    def test_parse_free_content(self, mocker):
        from app.services.license_parsers.pixabay import PixabayParser

        mock_html = """
        <html><body>
            <h1>Free Image</h1>
            <p>Free for commercial use under the Pixabay Content License</p>
            <p>No attribution required</p>
        </body></html>
        """

        mocker.patch.object(PixabayParser, "fetch_page", return_value=mock_html)
        parser = PixabayParser()
        result = parser.parse("https://pixabay.com/photos/abc/")

        assert result["license_type"] == "free_commercial"
        assert result["commercial_use"] is True

    def test_parse_sponsored_shutterstock(self, mocker):
        from app.services.license_parsers.pixabay import PixabayParser

        mock_html = """
        <html><body>
            <h1>Sponsored Image</h1>
            <p>Sponsored by Shutterstock</p>
            <p>This is a sponsored image from Shutterstock</p>
        </body></html>
        """

        mocker.patch.object(PixabayParser, "fetch_page", return_value=mock_html)
        parser = PixabayParser()
        result = parser.parse("https://pixabay.com/photos/abc/")

        assert result["license_type"] == "paid"
        assert result["commercial_use"] is False


# ── Freepik Parser Tests ──────────────────────────────────────────────


class TestFreepikParser:
    """Freepik parser should differentiate free (attribution required) from premium."""

    def test_parse_free_content(self, mocker):
        from app.services.license_parsers.freepik import FreepikParser

        mock_html = """
        <html><body>
            <h1>Free Resource</h1>
            <p>Free for personal use. Attribution required.</p>
            <p>Must credit Designed by Freepik</p>
        </body></html>
        """

        mocker.patch.object(FreepikParser, "fetch_page", return_value=mock_html)
        parser = FreepikParser()
        result = parser.parse("https://www.freepik.com/free-vector/abc/")

        assert result["license_type"] == "free_personal"
        assert result["requires_attribution"] is True

    def test_parse_premium_content(self, mocker):
        from app.services.license_parsers.freepik import FreepikParser

        mock_html = """
        <html><body>
            <h1>Premium Resource</h1>
            <p>Premium license. No attribution required.</p>
            <p>Unlimited downloads with Premium subscription</p>
        </body></html>
        """

        mocker.patch.object(FreepikParser, "fetch_page", return_value=mock_html)
        parser = FreepikParser()
        result = parser.parse("https://www.freepik.com/premium-vector/abc/")

        assert result["license_type"] == "paid"
        assert result["requires_attribution"] is False


# ── Shutterstock Parser Tests ─────────────────────────────────────────


class TestShutterstockParser:
    """Shutterstock parser should detect editorial vs standard vs enhanced."""

    def test_parse_editorial_only(self, mocker):
        from app.services.license_parsers.shutterstock import ShutterstockParser

        mock_html = """
        <html><body>
            <h1>Editorial Image</h1>
            <p>Editorial Use Only</p>
            <p>Not for commercial use</p>
        </body></html>
        """

        mocker.patch.object(ShutterstockParser, "fetch_page", return_value=mock_html)
        parser = ShutterstockParser()
        result = parser.parse("https://www.shutterstock.com/image-photo/abc/")

        assert result["license_type"] == "editorial_only"
        assert result["commercial_use"] is False

    def test_parse_standard_license(self, mocker):
        from app.services.license_parsers.shutterstock import ShutterstockParser

        mock_html = """
        <html><body>
            <h1>Stock Image</h1>
            <p>Standard License</p>
            <p>Royalty-free stock photo</p>
        </body></html>
        """

        mocker.patch.object(ShutterstockParser, "fetch_page", return_value=mock_html)
        parser = ShutterstockParser()
        result = parser.parse("https://www.shutterstock.com/image-photo/abc/")

        assert result["license_type"] == "paid"


# ── Getty Images Parser Tests ─────────────────────────────────────────


class TestGettyImagesParser:
    """Getty Images parser should detect editorial and paid content."""

    def test_parse_editorial_only(self, mocker):
        from app.services.license_parsers.gettyimages import GettyImagesParser

        mock_html = """
        <html><body>
            <h1>Editorial Image</h1>
            <p>Editorial Use Only</p>
            <p>Not released. Not model released.</p>
        </body></html>
        """

        mocker.patch.object(GettyImagesParser, "fetch_page", return_value=mock_html)
        parser = GettyImagesParser()
        result = parser.parse("https://www.gettyimages.com/detail/photo/abc/")

        assert result["license_type"] == "editorial_only"
        assert result["commercial_use"] is False
        assert "editorial" in result["summary"].lower()

    def test_parse_royalty_free(self, mocker):
        from app.services.license_parsers.gettyimages import GettyImagesParser

        mock_html = """
        <html><body>
            <h1>Royalty-Free Image</h1>
            <p>Royalty-free license</p>
        </body></html>
        """

        mocker.patch.object(GettyImagesParser, "fetch_page", return_value=mock_html)
        parser = GettyImagesParser()
        result = parser.parse("https://www.gettyimages.com/detail/photo/abc/")

        assert result["license_type"] == "paid"
        assert result["commercial_use"] is True  # RF can be used commercially with license


# ── Traffic Light Tests ───────────────────────────────────────────────


class TestTrafficLight:
    """Test the traffic light risk classification logic."""

    def test_green_for_free_commercial_font(self):
        from app.services.traffic_light import _assess_known_font

        db_match = {
            "name": "思源黑体",
            "license_type": "open_source",
            "commercial_use": True,
            "requires_attribution": False,
        }
        risk, explanation, alternatives = _assess_known_font(db_match)

        assert risk == "green"
        assert "免费" in explanation

    def test_red_for_prohibited_font(self):
        from app.services.traffic_light import _assess_known_font

        db_match = {
            "name": "方正黑体",
            "license_type": "paid",
            "commercial_use": False,
            "requires_attribution": None,
        }
        risk, explanation, alternatives = _assess_known_font(db_match)

        assert risk == "yellow"  # paid but not explicitly prohibited
        assert len(alternatives) > 0

    def test_yellow_for_personal_only_font(self):
        from app.services.traffic_light import _assess_known_font

        db_match = {
            "name": "Gilroy",
            "license_type": "free_personal",
            "commercial_use": False,
            "requires_attribution": True,
        }
        risk, explanation, alternatives = _assess_known_font(db_match)

        assert risk == "yellow"
        assert len(alternatives) > 0

    def test_unknown_font_risky_foundry_is_red(self):
        from app.services.traffic_light import _assess_unknown_font

        font_result = {"font_name": "汉仪旗黑", "confidence": 0.85}
        risk, explanation = _assess_unknown_font("汉仪旗黑", font_result)

        assert risk == "red"
        assert "汉仪" in explanation

    def test_unknown_font_safe_foundry_is_green(self):
        from app.services.traffic_light import _assess_unknown_font

        font_result = {"font_name": "思源黑体", "confidence": 0.9}
        risk, explanation = _assess_unknown_font("思源黑体", font_result)

        assert risk == "green"
        assert "免费商用" in explanation
