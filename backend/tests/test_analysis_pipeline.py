"""
Integration test for the full image analysis pipeline.

Tests the traffic light output for a known test case
with a sample image containing known fonts.
"""

import pytest
import json


class TestReportGeneration:
    """Test report generation with known font risks and source risks."""

    def test_generate_report_all_green(self):
        """Report with all green results should have overall_risk green."""
        from app.services.report_generator import generate_report

        font_risks = [
            {
                "name": "思源黑体",
                "text_sample": "你好世界",
                "risk": "green",
                "explanation": "思源黑体是免费可商用的开源字体",
                "alternatives": [],
            },
            {
                "name": "Roboto",
                "text_sample": "Hello",
                "risk": "green",
                "explanation": "Roboto 是免费可商用的开源字体",
                "alternatives": [],
            },
        ]

        source_risk = {
            "source_url": "https://unsplash.com/photos/abc",
            "risk": "green",
            "explanation": "Unsplash 图片可免费商用",
            "alternatives": [],
        }

        report = generate_report(
            font_risks=font_risks,
            source_risk=source_risk,
            claude_api_key="",  # Will use fallback summary
        )

        assert report["overall_risk"] == "green"
        assert len(report["fonts"]) == 2
        assert report["image_source"] is not None
        assert report["image_source"]["risk"] == "green"
        assert len(report["summary"]) > 0
        assert "恭喜" in report["summary"]

    def test_generate_report_with_red_fonts(self):
        """Report with red fonts should have overall_risk red."""
        from app.services.report_generator import generate_report

        font_risks = [
            {
                "name": "方正黑体",
                "text_sample": "标题文字",
                "risk": "red",
                "explanation": "方正黑体商业使用需购买授权",
                "alternatives": ["思源黑体", "阿里巴巴普惠体"],
            },
            {
                "name": "Arial",
                "text_sample": "Body text",
                "risk": "green",
                "explanation": "Arial 可免费商用",
                "alternatives": [],
            },
        ]

        source_risk = {
            "source_url": "https://shutterstock.com/photo/xyz",
            "risk": "yellow",
            "explanation": "Shutterstock 需要购买授权",
            "alternatives": ["https://unsplash.com"],
        }

        report = generate_report(
            font_risks=font_risks,
            source_risk=source_risk,
            claude_api_key="",
        )

        assert report["overall_risk"] == "red"
        assert len(report["fonts"]) == 2
        assert report["fonts"][0]["risk"] == "red"
        assert len(report["fonts"][0]["alternatives"]) == 2
        assert "替换" in report["summary"]

    def test_generate_report_yellow_mixed(self):
        """Mixed yellow and green should produce yellow overall."""
        from app.services.report_generator import generate_report

        font_risks = [
            {
                "name": "未知字体",
                "text_sample": "test",
                "risk": "yellow",
                "explanation": "无法确认授权状态",
                "alternatives": ["思源黑体"],
            },
        ]

        report = generate_report(
            font_risks=font_risks,
            source_risk=None,
            claude_api_key="",
        )

        assert report["overall_risk"] == "yellow"
        assert report["image_source"] is None
        assert len(report["summary"]) > 0

    def test_generate_report_empty(self):
        """Report with no risks should still be valid."""
        from app.services.report_generator import generate_report

        report = generate_report(
            font_risks=[],
            source_risk=None,
            claude_api_key="",
        )

        assert report["overall_risk"] == "green"
        assert report["fonts"] == []
        assert report["image_source"] is None
        assert len(report["summary"]) > 0


class TestTrafficLightSourceClassification:
    """Test source risk classification."""

    def test_unsplash_is_green(self):
        from app.services.traffic_light import classify_source_risk

        search_results = [
            {
                "url": "https://unsplash.com/photos/abc",
                "domain": "unsplash.com",
                "title": "Free photo",
                "snippet": "...",
                "license_info": {
                    "license_type": "free_commercial",
                    "commercial_use": True,
                    "requires_attribution": False,
                    "summary": "Free for commercial use",
                },
            }
        ]

        result = classify_source_risk(search_results)
        assert result is not None
        assert result["risk"] == "green"

    def test_gettyimages_is_red(self):
        from app.services.traffic_light import classify_source_risk

        search_results = [
            {
                "url": "https://www.gettyimages.com/detail/photo/test",
                "domain": "gettyimages.com",
                "title": "Stock photo",
                "snippet": "...",
                "license_info": {
                    "license_type": "paid",
                    "commercial_use": False,
                    "requires_attribution": None,
                    "summary": "Paid license required",
                },
            }
        ]

        result = classify_source_risk(search_results)
        assert result is not None
        assert result["risk"] == "red"
        assert "getty" in result["explanation"].lower()

    def test_no_results_returns_none(self):
        from app.services.traffic_light import classify_source_risk

        result = classify_source_risk([])
        assert result is None


class TestOCRService:
    """Basic OCR service tests (without actual PaddleOCR dependency)."""

    def test_extract_text_handles_missing_file(self):
        """Should handle missing image files gracefully."""
        from app.services.ocr import extract_text_from_image

        results = extract_text_from_image("/nonexistent/image.png")

        # Should return empty list or not crash
        assert isinstance(results, list)
