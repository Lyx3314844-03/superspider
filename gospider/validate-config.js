#!/usr/bin/env node
/**
 * GoSpider 配置验证器
 */

import * as fs from 'fs';
import * as path from 'path';

const REQUIRED_ENV = ['REDIS_URL', 'LOG_LEVEL', 'OUTPUT_DIR'];
const REQUIRED_PACKAGES = [
    'puppeteer',
    'playwright', 
    'express',
    'ioredis',
    'cheerio',
    'ws',
    'xpath',
    'xmldom'
];

function checkEnv() {
    console.log('📋 检查环境变量...\n');
    
    const missing = [];
    for (const env of REQUIRED_ENV) {
        if (!process.env[env]) {
            missing.push(env);
            console.log(`❌ ${env} 未设置`);
        } else {
            console.log(`✅ ${env} 已设置`);
        }
    }
    
    if (missing.length > 0) {
        console.log(`\n⚠️  缺少环境变量：${missing.join(', ')}`);
        console.log('建议：复制 .env.example 为 .env 并填写值\n');
    } else {
        console.log('\n✅ 所有环境变量已配置\n');
    }
    
    return missing.length === 0;
}

function checkPackages() {
    console.log('📦 检查依赖包...\n');
    
    const packageJson = path.join(process.cwd(), 'package.json');
    if (!fs.existsSync(packageJson)) {
        console.log('❌ package.json 不存在');
        return false;
    }
    
    const pkg = JSON.parse(fs.readFileSync(packageJson, 'utf-8'));
    const dependencies = { ...pkg.dependencies, ...pkg.devDependencies };
    
    const missing = [];
    for (const pkg of REQUIRED_PACKAGES) {
        if (!dependencies[pkg]) {
            missing.push(pkg);
            console.log(`❌ ${pkg} 未安装`);
        } else {
            console.log(`✅ ${pkg} 已安装 (${dependencies[pkg]})`);
        }
    }
    
    if (missing.length > 0) {
        console.log(`\n⚠️  缺少依赖包：${missing.join(', ')}`);
        console.log('运行：npm install\n');
    } else {
        console.log('\n✅ 所有依赖包已安装\n');
    }
    
    return missing.length === 0;
}

function checkFiles() {
    console.log('📁 检查文件...\n');
    
    const requiredFiles = [
        'enhanced.js',
        '.env.example'
    ];
    
    const missing = [];
    for (const file of requiredFiles) {
        if (!fs.existsSync(file)) {
            missing.push(file);
            console.log(`❌ ${file} 不存在`);
        } else {
            console.log(`✅ ${file} 存在`);
        }
    }
    
    if (missing.length > 0) {
        console.log(`\n⚠️  缺少文件：${missing.join(', ')}\n`);
    } else {
        console.log('\n✅ 所有文件存在\n');
    }
    
    return missing.length === 0;
}

// 主函数
console.log('╔════════════════════════════════════════════════════════╗');
console.log('║     GoSpider 配置验证器                                ║');
console.log('╚════════════════════════════════════════════════════════╝\n');

const envOk = checkEnv();
const packagesOk = checkPackages();
const filesOk = checkFiles();

console.log('╔════════════════════════════════════════════════════════╗');
console.log('║     验证结果                                            ║');
console.log('╚════════════════════════════════════════════════════════╝\n');

if (envOk && packagesOk && filesOk) {
    console.log('✅ 所有检查通过！GoSpider 已准备就绪。\n');
    process.exit(0);
} else {
    console.log('⚠️  部分检查未通过，请修复上述问题。\n');
    process.exit(1);
}
