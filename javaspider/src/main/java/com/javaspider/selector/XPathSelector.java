package com.javaspider.selector;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.parser.Parser;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.xpath.*;
import java.util.ArrayList;
import java.util.List;

/**
 * XPath 选择器
 */
public class XPathSelector implements Selector {
    
    private final String xpathExpression;
    
    public XPathSelector(String xpathExpression) {
        this.xpathExpression = xpathExpression;
    }
    
    @Override
    public String select(String text) {
        if (text == null || text.isEmpty()) {
            return null;
        }
        
        try {
            Document document = Jsoup.parse(text, "", Parser.xmlParser());
            org.jsoup.helper.W3CDom w3CDom = new org.jsoup.helper.W3CDom();
            org.w3c.dom.Document w3cDoc = w3CDom.fromJsoup(document);
            
            XPathFactory xPathFactory = XPathFactory.newInstance();
            XPath xPath = xPathFactory.newXPath();
            
            NodeList nodeList = (NodeList) xPath.evaluate(
                xpathExpression,
                w3cDoc,
                XPathConstants.NODESET
            );
            
            if (nodeList.getLength() == 0) {
                return null;
            }
            
            Node node = nodeList.item(0);
            return nodeValue(node);
            
        } catch (Exception e) {
            throw new RuntimeException("XPath evaluation error", e);
        }
    }
    
    @Override
    public List<String> selectAll(String text) {
        List<String> results = new ArrayList<>();
        
        if (text == null || text.isEmpty()) {
            return results;
        }
        
        try {
            Document document = Jsoup.parse(text, "", Parser.xmlParser());
            org.jsoup.helper.W3CDom w3CDom = new org.jsoup.helper.W3CDom();
            org.w3c.dom.Document w3cDoc = w3CDom.fromJsoup(document);
            
            XPathFactory xPathFactory = XPathFactory.newInstance();
            XPath xPath = xPathFactory.newXPath();
            
            NodeList nodeList = (NodeList) xPath.evaluate(
                xpathExpression,
                w3cDoc,
                XPathConstants.NODESET
            );
            
            for (int i = 0; i < nodeList.getLength(); i++) {
                Node node = nodeList.item(i);
                String value = nodeValue(node);
                if (value != null && !value.isEmpty()) {
                    results.add(value);
                }
            }
            
            return results;
            
        } catch (Exception e) {
            throw new RuntimeException("XPath evaluation error", e);
        }
    }
    
    public static XPathSelector of(String xpath) {
        return new XPathSelector(xpath);
    }

    private String nodeValue(Node node) {
        if (node == null) {
            return null;
        }
        String value = node.getNodeType() == Node.ATTRIBUTE_NODE ? node.getNodeValue() : node.getTextContent();
        return value == null ? null : value.trim();
    }
}
