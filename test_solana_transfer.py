"""
Solana 转账集成测试
"""

import unittest
import json
from unittest.mock import patch, MagicMock
from solana_transfer import generate_signature, batch_transfer, query_transfer_status, execute_solana_transfer


class TestSolanaTransfer(unittest.TestCase):
    """Solana 转账函数测试"""
    
    def test_generate_signature(self):
        """测试签名生成"""
        # 官方示例
        params = {
            "appid": "AxyA5555GAQ2fgqQy",
            "asset_symbol": "x2c",
            "batch_id": "KUGjbW2bMa4t9CysrvGEzP",
            "callback_url": "http://127.0.0.1:8020/do",
            "chain": "sol",
            "default_from_address": "BXytRkCtk6eLPv2c2fWib3bAPpDmZvUo735JLrAhA1Rp",
            "timestamp": 1766644279,
            "transfers": [
                {
                    "amount": "0.1",
                    "callback_url": "",
                    "from_address": "",
                    "memo": "req1 memo",
                    "request_id": "req10",
                    "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p"
                }
            ]
        }
        
        signature = generate_signature(params, "DXrocNWEBkWS38Rp5Br1fcOZ0aHg3Unmu")
        expected = "D723C7EFF18E1E25301FC503BE2B22B9"
        
        self.assertEqual(signature, expected, f"Signature mismatch: got {signature}, expected {expected}")
        print(f"✅ Signature generation test passed: {signature}")
    
    def test_signature_with_empty_values(self):
        """测试签名生成时过滤空值"""
        params = {
            "appid": "test_app",
            "batch_id": "test_batch",
            "empty_field": "",
            "none_field": None,
            "valid_field": "value"
        }
        
        # 应该不抛出异常
        signature = generate_signature(params)
        self.assertIsNotNone(signature)
        self.assertEqual(len(signature), 32)  # MD5 哈希长度
        print(f"✅ Empty values filtering test passed")
    
    @patch('solana_transfer.requests.post')
    def test_batch_transfer_success(self, mock_post):
        """测试批量转账成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "batch_id": "test_batch_123",
                "status": "PROCESSING",
                "transfers": [
                    {
                        "request_id": "req_1",
                        "status": "PENDING",
                        "tx_hash": "",
                        "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
                        "amount": "0.1"
                    }
                ]
            },
            "msg": "Success"
        }
        mock_post.return_value = mock_response
        
        result = batch_transfer(
            to_address="7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
            amount="0.1",
            withdrawal_id=1,
            asset_type="x2c"
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "PENDING")
        self.assertEqual(result["to_address"], "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p")
        self.assertEqual(result["amount"], "0.1")
        print(f"✅ Batch transfer success test passed")
    
    @patch('solana_transfer.requests.post')
    def test_batch_transfer_api_error(self, mock_post):
        """测试批量转账 API 错误"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 1,
            "msg": "Invalid parameters"
        }
        mock_post.return_value = mock_response
        
        result = batch_transfer(
            to_address="invalid_address",
            amount="0.1",
            withdrawal_id=1
        )
        
        self.assertIsNone(result)
        print(f"✅ Batch transfer API error test passed")
    
    @patch('solana_transfer.requests.post')
    def test_query_transfer_status_success(self, mock_post):
        """测试查询转账状态成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "batch_id": "test_batch_123",
                "status": "SUCCESS",
                "transfers": [
                    {
                        "request_id": "req_1",
                        "status": "SUCCESS",
                        "tx_hash": "Lz4i1vZkwXqDGHA6b3sGozp6rk41pA6WWXWY2PhdW6wUVi1nmabeZEcXzeHA1VBUwUGiSPiTkvfE9LX7LMNY6Nh",
                        "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
                        "amount": "0.1"
                    }
                ]
            },
            "msg": "Success"
        }
        mock_post.return_value = mock_response
        
        result = query_transfer_status("test_batch_123")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(len(result["transfers"]), 1)
        self.assertEqual(result["transfers"][0]["status"], "SUCCESS")
        print(f"✅ Query transfer status success test passed")
    
    @patch('solana_transfer.query_transfer_status')
    @patch('solana_transfer.batch_transfer')
    def test_execute_solana_transfer_success(self, mock_batch, mock_query):
        """测试执行 Solana 转账成功"""
        # 模拟 batch_transfer 返回
        mock_batch.return_value = {
            "batch_id": "test_batch_123",
            "request_id": "req_1",
            "status": "PENDING",
            "tx_hash": "",
            "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
            "amount": "0.1"
        }
        
        # 模拟 query_transfer_status 返回成功
        mock_query.return_value = {
            "batch_id": "test_batch_123",
            "status": "SUCCESS",
            "transfers": [
                {
                    "request_id": "req_1",
                    "status": "SUCCESS",
                    "tx_hash": "Lz4i1vZkwXqDGHA6b3sGozp6rk41pA6WWXWY2PhdW6wUVi1nmabeZEcXzeHA1VBUwUGiSPiTkvfE9LX7LMNY6Nh",
                    "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
                    "amount": "0.1"
                }
            ]
        }
        
        tx_hash = execute_solana_transfer(
            to_address="7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
            amount="0.1",
            withdrawal_id=1
        )
        
        self.assertIsNotNone(tx_hash)
        self.assertEqual(tx_hash, "Lz4i1vZkwXqDGHA6b3sGozp6rk41pA6WWXWY2PhdW6wUVi1nmabeZEcXzeHA1VBUwUGiSPiTkvfE9LX7LMNY6Nh")
        print(f"✅ Execute Solana transfer success test passed")
    
    @patch('solana_transfer.batch_transfer')
    def test_execute_solana_transfer_failed(self, mock_batch):
        """测试执行 Solana 转账失败"""
        mock_batch.return_value = None
        
        tx_hash = execute_solana_transfer(
            to_address="invalid_address",
            amount="0.1",
            withdrawal_id=1
        )
        
        self.assertIsNone(tx_hash)
        print(f"✅ Execute Solana transfer failed test passed")


if __name__ == '__main__':
    # 运行测试
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSolanaTransfer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印总结
    print("\n" + "="*50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")

    @patch('solana_transfer.query_transfer_status')
    @patch('solana_transfer.batch_transfer')
    def test_execute_solana_transfer_cancelled(self, mock_batch, mock_query):
        """测试执行 Solana 转账被取消"""
        mock_batch.return_value = {
            "batch_id": "test_batch_123",
            "request_id": "req_1",
            "status": "PENDING",
            "tx_hash": "",
            "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
            "amount": "0.1"
        }
        
        # 模拟转账被取消
        mock_query.return_value = {
            "batch_id": "test_batch_123",
            "status": "PROCESSING",
            "transfers": [
                {
                    "request_id": "req_1",
                    "status": "CANCELLED",
                    "tx_hash": "",
                    "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
                    "amount": "0.1"
                }
            ]
        }
        
        tx_hash = execute_solana_transfer(
            to_address="7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
            amount="0.1",
            withdrawal_id=1
        )
        
        self.assertIsNone(tx_hash)
        print(f"✅ Execute Solana transfer cancelled test passed")
    
    @patch('solana_transfer.query_transfer_status')
    @patch('solana_transfer.batch_transfer')
    def test_execute_solana_transfer_processing(self, mock_batch, mock_query):
        """测试执行 Solana 转账处理中状态"""
        mock_batch.return_value = {
            "batch_id": "test_batch_123",
            "request_id": "req_1",
            "status": "PENDING",
            "tx_hash": "",
            "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
            "amount": "0.1"
        }
        
        # 模拟多次查询，最后成功
        mock_query.side_effect = [
            {
                "batch_id": "test_batch_123",
                "status": "PROCESSING",
                "transfers": [{"request_id": "req_1", "status": "PROCESSING", "tx_hash": ""}]
            },
            {
                "batch_id": "test_batch_123",
                "status": "SUCCESS",
                "transfers": [{
                    "request_id": "req_1",
                    "status": "SUCCESS",
                    "tx_hash": "Lz4i1vZkwXqDGHA6b3sGozp6rk41pA6WWXWY2PhdW6wUVi1nmabeZEcXzeHA1VBUwUGiSPiTkvfE9LX7LMNY6Nh"
                }]
            }
        ]
        
        tx_hash = execute_solana_transfer(
            to_address="7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
            amount="0.1",
            withdrawal_id=1
        )
        
        self.assertIsNotNone(tx_hash)
        self.assertEqual(tx_hash, "Lz4i1vZkwXqDGHA6b3sGozp6rk41pA6WWXWY2PhdW6wUVi1nmabeZEcXzeHA1VBUwUGiSPiTkvfE9LX7LMNY6Nh")
        print(f"✅ Execute Solana transfer processing test passed")
