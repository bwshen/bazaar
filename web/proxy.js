#!/usr/bin/env node
'use strict';

const http = require('http'),
  httpProxy = require('http-proxy'),
  serveStatic = require('serve-static'),
  finalhandler = require('finalhandler');

const proxyServe = httpProxy.createProxyServer({
  target: 'http://localhost:3000',
  secure: false
});

const backendProxy = httpProxy.createProxyServer({
	target: 'http://localhost:5000',
	secure: false
});
backendProxy.on('proxyReq', function(proxyReq, req, res, options) {
	proxyReq.setHeader('host', 'localhost:5000');
});

const bodegaProxy = httpProxy.createProxyServer({
  target: 'https://bodega.rubrik-lab.com',
  secure: false
});
bodegaProxy.on('proxyReq', function(proxyReq, req, res, options) {
   proxyReq.setHeader('host', 'bodega.rubrik-lab.com');
   proxyReq.setHeader('referer', 'https://bodega.rubrik-lab.com/');
});

const server = http.createServer(function(req, res) {
  if (req.url.includes('/api')) {
    bodegaProxy.web(req, res);
  } 
	else if (req.url.includes('order_times')) {
		backendProxy.web(req, res);
	}
	else {
    proxyServe.web(req, res);
  }
});

server.listen(4000);
