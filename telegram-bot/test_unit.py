import unittest

from client import REST_TOOL, assert_rest_allowed, mcp_tools_to_openai
from moneyfmt import format_inr


class MoneyFmtTests(unittest.TestCase):
    def test_indian_grouping(self):
        self.assertEqual(format_inr("123456.7"), "₹1,23,456.70")
        self.assertEqual(format_inr("1000"), "₹1,000.00")
        self.assertEqual(format_inr("-50"), "-₹50.00")

    def test_negative(self):
        self.assertEqual(format_inr("-123456.78"), "-₹1,23,456.78")

    def test_rejects_garbage(self):
        with self.assertRaises(ValueError):
            format_inr("not-money")


class RestGuardTests(unittest.TestCase):
    def test_allows_accounts(self):
        assert_rest_allowed("GET", "/api/accounts", None)

    def test_blocks_password(self):
        with self.assertRaises(ValueError):
            assert_rest_allowed("PATCH", "/api/users/me", {"password": "x"})

    def test_blocks_2fa(self):
        with self.assertRaises(ValueError):
            assert_rest_allowed("POST", "/api/auth/2fa/setup", {})

    def test_blocks_create_admin(self):
        with self.assertRaises(ValueError):
            assert_rest_allowed("POST", "/api/setup/create-admin", {"email": "a@b.c"})

    def test_requires_api_prefix(self):
        with self.assertRaises(ValueError):
            assert_rest_allowed("GET", "/health", None)


class ToolSchemaTests(unittest.TestCase):
    def test_mcp_to_openai_includes_rest_fallback(self):
        tools = mcp_tools_to_openai(
            [
                {
                    "name": "list_accounts",
                    "description": "List accounts",
                    "inputSchema": {"type": "object", "properties": {}},
                    "_securo": {"is_proposal": False},
                },
                {
                    "name": "propose_create_transaction",
                    "description": "Add a txn",
                    "inputSchema": {"type": "object", "properties": {"apply": {"type": "boolean"}}},
                    "_securo": {"is_proposal": True},
                },
            ]
        )
        names = [t["function"]["name"] for t in tools]
        self.assertEqual(names[-1], REST_TOOL["function"]["name"])
        self.assertIn("list_accounts", names)
        propose = next(t for t in tools if t["function"]["name"] == "propose_create_transaction")
        self.assertIn("apply=false", propose["function"]["description"])


if __name__ == "__main__":
    unittest.main()
