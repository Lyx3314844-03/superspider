def test_source_tree_exposes_nested_advanced_package():
    from pyspider.advanced import UltimateConfig, create_ultimate_spider

    config = UltimateConfig(max_concurrency=1)
    spider = create_ultimate_spider(config)

    assert spider.config.max_concurrency == 1


def test_source_tree_exposes_nested_node_reverse_package():
    from pyspider.node_reverse import NodeReverseClient

    client = NodeReverseClient("http://localhost:3000")
    assert client.base_url == "http://localhost:3000"


def test_source_tree_exposes_nested_encrypted_package():
    from pyspider.encrypted import EncryptedSiteCrawlerEnhanced

    crawler = EncryptedSiteCrawlerEnhanced("http://localhost:3000")
    assert crawler.reverse_client.base_url == "http://localhost:3000"
