package com.javaspider.util;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * ResourceManager 单元测试
 */
@DisplayName("ResourceManager 测试")
class ResourceManagerTest {

    private ResourceManager resourceManager;
    private TestCloseableResource testResource;

    static class TestCloseableResource implements AutoCloseable {
        private final AtomicBoolean closed = new AtomicBoolean(false);
        private final String name;

        TestCloseableResource(String name) {
            this.name = name;
        }

        @Override
        public void close() {
            closed.set(true);
        }

        boolean isClosed() {
            return closed.get();
        }

        String getName() {
            return name;
        }
    }

    @BeforeEach
    void setUp() {
        // 创建新的资源管理器实例进行测试
        testResource = new TestCloseableResource("test-resource");
    }

    @AfterEach
    void tearDown() {
        if (resourceManager != null) {
            resourceManager.close();
        }
        ResourceManager.getInstance().close();
    }

    @Test
    @DisplayName("测试单例模式")
    void testSingleton() {
        ResourceManager instance1 = ResourceManager.getInstance();
        ResourceManager instance2 = ResourceManager.getInstance();
        
        assertSame(instance1, instance2, "单例应该返回相同实例");
    }

    @Test
    @DisplayName("测试注册资源")
    void testRegisterResource() {
        resourceManager = new ResourceManager();
        
        TestCloseableResource resource = new TestCloseableResource("test1");
        ResourceManager result = resourceManager.register(resource);
        
        assertSame(resourceManager, result, "应该支持链式调用");
        assertEquals(1, resourceManager.getResourceCount());
    }

    @Test
    @DisplayName("测试注册 null 资源")
    void testRegisterNullResource() {
        resourceManager = new ResourceManager();
        
        assertDoesNotThrow(() -> resourceManager.register(null));
        // 资源数量不应该增加
    }

    @Test
    @DisplayName("测试注册 ProxyPool")
    void testRegisterProxyPool() {
        resourceManager = new ResourceManager();
        
        com.javaspider.antibot.ProxyPool proxyPool = new com.javaspider.antibot.ProxyPool();
        ResourceManager result = resourceManager.registerProxyPool(proxyPool);
        
        assertSame(resourceManager, result);
        assertEquals(1, resourceManager.getResourceCount());
    }

    @Test
    @DisplayName("测试关闭资源")
    void testCloseResources() throws Exception {
        resourceManager = new ResourceManager();
        
        TestCloseableResource resource1 = new TestCloseableResource("resource1");
        TestCloseableResource resource2 = new TestCloseableResource("resource2");
        
        resourceManager.register(resource1);
        resourceManager.register(resource2);
        
        resourceManager.close();
        
        assertTrue(resource1.isClosed(), "resource1 应该被关闭");
        assertTrue(resource2.isClosed(), "resource2 应该被关闭");
        assertFalse(resourceManager.isClosing());
    }

    @Test
    @DisplayName("测试资源关闭顺序（倒序）")
    void testCloseOrder() throws Exception {
        resourceManager = new ResourceManager();
        
        List<String> closeOrder = new ArrayList<>();
        
        TestCloseableResource resource1 = new TestCloseableResource("first") {
            @Override
            public void close() {
                super.close();
                closeOrder.add(getName());
            }
        };
        
        TestCloseableResource resource2 = new TestCloseableResource("second") {
            @Override
            public void close() {
                super.close();
                closeOrder.add(getName());
            }
        };
        
        TestCloseableResource resource3 = new TestCloseableResource("third") {
            @Override
            public void close() {
                super.close();
                closeOrder.add(getName());
            }
        };
        
        resourceManager.register(resource1);
        resourceManager.register(resource2);
        resourceManager.register(resource3);
        
        resourceManager.close();
        
        // 应该倒序关闭
        assertEquals("third", closeOrder.get(0));
        assertEquals("second", closeOrder.get(1));
        assertEquals("first", closeOrder.get(2));
    }

    @Test
    @DisplayName("测试关闭时异常处理")
    void testCloseWithException() {
        resourceManager = new ResourceManager();
        
        TestCloseableResource normalResource = new TestCloseableResource("normal");
        
        TestCloseableResource throwingResource = new TestCloseableResource("throwing") {
            @Override
            public void close() {
                throw new RuntimeException("Close failed");
            }
        };
        
        resourceManager.register(normalResource);
        resourceManager.register(throwingResource);
        
        // 不应该抛出异常
        assertDoesNotThrow(() -> resourceManager.close());
        
        // 正常资源应该被关闭
        assertTrue(normalResource.isClosed());
    }

    @Test
    @DisplayName("测试重复关闭")
    void testMultipleClose() throws Exception {
        resourceManager = new ResourceManager();
        
        TestCloseableResource resource = new TestCloseableResource("test");
        resourceManager.register(resource);
        
        resourceManager.close();
        assertTrue(resource.isClosed());
        
        // 再次关闭不应该抛出异常或重复关闭
        assertDoesNotThrow(() -> resourceManager.close());
    }

    @Test
    @DisplayName("测试移除资源")
    void testUnregisterResource() {
        resourceManager = new ResourceManager();
        
        TestCloseableResource resource = new TestCloseableResource("test");
        resourceManager.register(resource);
        assertEquals(1, resourceManager.getResourceCount());
        
        resourceManager.unregister(resource);
        assertEquals(0, resourceManager.getResourceCount());
    }

    @Test
    @DisplayName("测试关闭钩子注册")
    void testShutdownHookRegistration() {
        resourceManager = new ResourceManager();
        
        // 第一次注册应该成功
        assertDoesNotThrow(() -> resourceManager.registerShutdownHook());
        
        // 第二次注册不应该抛出异常（幂等）
        assertDoesNotThrow(() -> resourceManager.registerShutdownHook());
    }

    @Test
    @DisplayName("测试链式注册")
    void testChainedRegistration() {
        resourceManager = new ResourceManager();
        
        TestCloseableResource resource1 = new TestCloseableResource("test1");
        TestCloseableResource resource2 = new TestCloseableResource("test2");
        TestCloseableResource resource3 = new TestCloseableResource("test3");
        
        resourceManager
            .register(resource1)
            .register(resource2)
            .register(resource3);
        
        assertEquals(3, resourceManager.getResourceCount());
    }

    @Test
    @DisplayName("测试空资源管理器关闭")
    void testCloseEmptyManager() {
        resourceManager = new ResourceManager();
        
        assertDoesNotThrow(() -> resourceManager.close());
        assertFalse(resourceManager.isClosing());
    }

    @Test
    @DisplayName("测试资源状态")
    void testResourceState() {
        resourceManager = new ResourceManager();
        
        assertFalse(resourceManager.isClosing());
        assertEquals(0, resourceManager.getResourceCount());
        
        resourceManager.register(new TestCloseableResource("test"));
        assertEquals(1, resourceManager.getResourceCount());
        assertFalse(resourceManager.isClosing());
        
        resourceManager.close();
        assertFalse(resourceManager.isClosing());
    }
}
