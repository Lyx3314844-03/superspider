#!/usr/bin/env node
/**
 * 统一日志系统
 * 
 * 使用示例:
 * import logger from './logger.js';
 * 
 * logger.info('信息消息');
 * logger.warn('警告消息');
 * logger.error('错误消息');
 * logger.debug('调试消息');
 */

import * as fs from 'fs';
import * as path from 'path';

const LOG_LEVELS = {
    error: 0,
    warn: 1,
    info: 2,
    debug: 3
};

class Logger {
    constructor(name, options = {}) {
        this.name = name;
        this.level = options.level || process.env.LOG_LEVEL || 'info';
        this.outputDir = options.outputDir || process.env.OUTPUT_DIR || './logs';
        
        // 确保日志目录存在
        if (!fs.existsSync(this.outputDir)) {
            fs.mkdirSync(this.outputDir, { recursive: true });
        }
    }
    
    _shouldLog(level) {
        return LOG_LEVELS[level] <= LOG_LEVELS[this.level];
    }
    
    _formatMessage(level, message, data) {
        const timestamp = new Date().toISOString();
        const dataStr = data ? ` ${JSON.stringify(data)}` : '';
        return `[${timestamp}] [${level.toUpperCase()}] [${this.name}] ${message}${dataStr}`;
    }
    
    _write(message) {
        // 输出到控制台
        console.log(message);
        
        // 输出到文件
        const date = new Date().toISOString().split('T')[0];
        const logFile = path.join(this.outputDir, `${date}.log`);
        fs.appendFileSync(logFile, message + '\n', 'utf-8');
    }
    
    error(message, data) {
        if (this._shouldLog('error')) {
            this._write(this._formatMessage('error', message, data));
        }
    }
    
    warn(message, data) {
        if (this._shouldLog('warn')) {
            this._write(this._formatMessage('warn', message, data));
        }
    }
    
    info(message, data) {
        if (this._shouldLog('info')) {
            this._write(this._formatMessage('info', message, data));
        }
    }
    
    debug(message, data) {
        if (this._shouldLog('debug')) {
            this._write(this._formatMessage('debug', message, data));
        }
    }
}

// 创建默认日志实例
const defaultLogger = new Logger('default');

export default defaultLogger;
export { Logger };
