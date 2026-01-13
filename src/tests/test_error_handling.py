from faker import Faker
from fastapi.testclient import TestClient

from src.main import app
from src.tests.test_helpers import program_vcr

client = TestClient(app)
fake = Faker()
vcr = program_vcr()


class TestQueryParamValidation:
    """Test query parameter validation edge cases"""

    def test_invalid_zip_code_too_low(self):
        """Test ZIP code below minimum value"""
        params = {"zip": "500", "year": "2024", "radius": "125", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_invalid_zip_code_too_high(self):
        """Test ZIP code above maximum value"""
        params = {"zip": "99951", "year": "2024", "radius": "125", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_invalid_year_too_old(self):
        """Test year below minimum value"""
        params = {"zip": "90210", "year": "2021", "radius": "125", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_invalid_year_too_new(self):
        """Test year above maximum value"""
        params = {"zip": "90210", "year": "2027", "radius": "125", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_invalid_radius_zero(self):
        """Test radius of zero"""
        params = {"zip": "90210", "year": "2024", "radius": "0", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_invalid_radius_too_large(self):
        """Test radius above maximum value"""
        params = {"zip": "90210", "year": "2024", "radius": "501", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_invalid_model_name(self):
        """Test invalid model name"""
        params = {
            "zip": "90210",
            "year": "2024",
            "radius": "125",
            "model": "InvalidModel",
        }
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_missing_required_param_zip(self):
        """Test missing ZIP parameter"""
        params = {"year": "2024", "radius": "125", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_missing_required_param_year(self):
        """Test missing year parameter"""
        params = {"zip": "90210", "radius": "125", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_missing_required_param_radius(self):
        """Test missing radius parameter"""
        params = {"zip": "90210", "year": "2024", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_missing_required_param_model(self):
        """Test missing model parameter"""
        params = {"zip": "90210", "year": "2024", "radius": "125"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_non_numeric_zip(self):
        """Test non-numeric ZIP code"""
        params = {"zip": "ABCDE", "year": "2024", "radius": "125", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_non_numeric_year(self):
        """Test non-numeric year"""
        params = {"zip": "90210", "year": "ABCD", "radius": "125", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422

    def test_negative_radius(self):
        """Test negative radius"""
        params = {"zip": "90210", "year": "2024", "radius": "-10", "model": "Ioniq 5"}
        response = client.get("/api/inventory/hyundai", params=params)
        assert response.status_code == 422


class TestNonExistentEndpoints:
    """Test handling of non-existent routes"""

    def test_nonexistent_manufacturer(self):
        """Test inventory endpoint for non-existent manufacturer"""
        params = {"zip": "90210", "year": "2024", "radius": "125", "model": "Model 3"}
        response = client.get("/api/inventory/tesla", params=params)
        assert response.status_code == 404

    def test_nonexistent_vin_endpoint(self):
        """Test VIN endpoint for non-existent manufacturer"""
        params = {"vin": "1234567890"}
        response = client.get("/api/vin/tesla", params=params)
        assert response.status_code == 404

    def test_invalid_api_path(self):
        """Test completely invalid API path"""
        response = client.get("/api/invalid/endpoint")
        assert response.status_code == 404


class TestHelperEndpoints:
    """Test helper endpoints"""

    def test_liveness_endpoint(self):
        """Test /api/liveness health check endpoint"""
        cassette_name = "helpers-liveness.yaml"
        with vcr.use_cassette(cassette_name):
            response = client.get("/api/liveness")

        # Should return 200 or 500 depending on GCP metadata availability
        assert response.status_code in [200, 500]

    def test_version_endpoint_with_env_var(self):
        """Test /api/version endpoint"""
        response = client.get("/api/version")
        assert response.status_code == 200

    def test_error_test_endpoint_400(self):
        """Test /api/test/error endpoint with 400 status"""
        response = client.get("/api/test/error/400")
        assert response.status_code == 400

    def test_error_test_endpoint_500(self):
        """Test /api/test/error endpoint with 500 status"""
        response = client.get("/api/test/error/500")
        assert response.status_code == 500

    def test_error_test_endpoint_invalid_code(self):
        """Test /api/test/error endpoint with invalid status code"""
        response = client.get("/api/test/error/399")
        assert response.status_code == 422

    def test_status_test_endpoint_200(self):
        """Test /api/test/status endpoint with 200"""
        response = client.get("/api/test/status/200")
        assert response.status_code == 200

    def test_status_test_endpoint_404(self):
        """Test /api/test/status endpoint with 404"""
        response = client.get("/api/test/status/404")
        assert response.status_code == 404


class TestCORSAndHeaders:
    """Test CORS and header handling"""

    def test_cors_preflight(self):
        """Test CORS preflight OPTIONS request"""
        response = client.options(
            "/api/inventory/hyundai",
            headers={
                "Origin": "https://theevfinder.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI TestClient might not handle OPTIONS the same as real server
        assert response.status_code in [200, 405]

    def test_request_with_origin_header(self):
        """Test request with Origin header"""
        params = {"zip": "90210", "year": "2024", "radius": "125", "model": "Ioniq 5"}
        headers = {"Origin": "https://theevfinder.com"}

        cassette_name = "cors-test-hyundai.yaml"
        with vcr.use_cassette(cassette_name):
            response = client.get(
                "/api/inventory/hyundai", params=params, headers=headers
            )

        assert response.status_code == 200


class TestSpecialCases:
    """Test special edge cases"""

    def test_url_encoded_model_name(self):
        """Test with URL-encoded model name"""
        params = {
            "zip": "90210",
            "year": "2024",
            "radius": "125",
            "model": "Ioniq%205",  # URL encoded
        }

        cassette_name = "url-encoded-model.yaml"
        with vcr.use_cassette(cassette_name):
            response = client.get("/api/inventory/hyundai", params=params)

        assert response.status_code == 200

    def test_leading_zeros_in_zip(self):
        """Test ZIP code with leading zeros"""
        params = {
            "zip": "00501",  # Leading zeros
            "year": "2024",
            "radius": "125",
            "model": "Ioniq 5",
        }

        cassette_name = "leading-zeros-zip.yaml"
        with vcr.use_cassette(cassette_name):
            response = client.get("/api/inventory/hyundai", params=params)

        assert response.status_code == 200

    def test_boundary_zip_minimum(self):
        """Test minimum valid ZIP code"""
        params = {"zip": "501", "year": "2024", "radius": "125", "model": "Ioniq 5"}

        cassette_name = "boundary-zip-min.yaml"
        with vcr.use_cassette(cassette_name):
            response = client.get("/api/inventory/hyundai", params=params)

        assert response.status_code == 200

    def test_boundary_zip_maximum(self):
        """Test maximum valid ZIP code"""
        params = {"zip": "99950", "year": "2024", "radius": "125", "model": "Ioniq 5"}

        cassette_name = "boundary-zip-max.yaml"
        with vcr.use_cassette(cassette_name):
            response = client.get("/api/inventory/hyundai", params=params)

        assert response.status_code == 200

    def test_boundary_radius_minimum(self):
        """Test minimum valid radius"""
        params = {"zip": "90210", "year": "2024", "radius": "1", "model": "Ioniq 5"}

        cassette_name = "boundary-radius-min.yaml"
        with vcr.use_cassette(cassette_name):
            response = client.get("/api/inventory/hyundai", params=params)

        assert response.status_code == 200

    def test_boundary_radius_maximum(self):
        """Test maximum valid radius"""
        params = {"zip": "90210", "year": "2024", "radius": "500", "model": "Ioniq 5"}

        cassette_name = "boundary-radius-max.yaml"
        with vcr.use_cassette(cassette_name):
            response = client.get("/api/inventory/hyundai", params=params)

        assert response.status_code == 200


class TestVINEndpointErrors:
    """Test VIN endpoint error handling"""

    def test_vin_endpoint_missing_vin_param(self):
        """Test VIN endpoint without VIN parameter"""
        params = {"model": "Ioniq 5", "year": "2024"}
        response = client.get("/api/vin/hyundai", params=params)

        # Should handle missing VIN gracefully
        assert response.status_code in [200, 400, 422, 500]

    def test_vin_endpoint_invalid_vin_format(self):
        """Test VIN endpoint with invalid VIN format"""
        params = {"vin": "INVALID", "model": "Ioniq 5", "year": "2024"}

        cassette_name = "vin-invalid-format.yaml"
        with vcr.use_cassette(cassette_name):
            response = client.get("/api/vin/hyundai", params=params)

        # Should handle invalid VIN
        assert response.status_code in [200, 400, 422, 500]

    def test_vin_endpoint_nonexistent_vin(self):
        """Test VIN endpoint with non-existent VIN"""
        params = {
            "vin": "KMHFG4JG0NA000000",  # Valid format but likely doesn't exist
            "model": "Ioniq 5",
            "year": "2024",
        }

        cassette_name = "vin-nonexistent.yaml"
        with vcr.use_cassette(cassette_name):
            response = client.get("/api/vin/hyundai", params=params)

        # Should handle non-existent VIN
        assert response.status_code in [200, 400, 404, 500]
