!(function() {

	"use strict";

	var preloader = function(opts) {
		var _this = this;
		_this.files = opts.files;
		_this.current = 0;
		_this.progress = opts.progress;
		_this.complete = opts.complete;

		_this.container = document.createElement('div');
		_this.container.style.cssText = 'position:absolute;left:-1000px;top:0;width:1px;height:1px;overflow:hidden';
		document.body.appendChild(_this.container);

		for (var i = 0; i < _this.files.length; i++) {
			var file = _this.files[i];
			var fileExt = file.split('.');
			var fileType = fileExt[fileExt.length - 1];
			if (fileType === 'css' || fileType === 'js' || fileType === 'json') {
				_this.loadResource(file);
			} else {
				_this.loadImage(file);
			}
		}
	}

	// 加载触发器
	preloader.prototype.loadTrigger = function(err, response) {
		var _this = this;
		_this.current++;
		_this.progress(err, response, (_this.current/_this.files.length * 100).toFixed(0));

		// 文件加载完成
		if (_this.current == _this.files.length) {
			_this.complete();
		}
	}

	// 图片加载器
	preloader.prototype.loadImage = function(file) {
		var _this = this;
		var image = new Image();

		image.onload = function() {
			_this.loadTrigger(null, image);
			image.onload = null;

			_this.container.appendChild(image);
		}

		image.onerror = function() {
			_this.loadTrigger(null, image);
			image.onload = null;
		}

		image.src = file;
	}

	// 资源加载器
	preloader.prototype.loadResource = function(file) {
		var _this = this;
		var request = new XMLHttpRequest();
		request.open('GET', file, true);

		request.addEventListener('load', function () {
			_this.loadTrigger(null, request.response);
		});
		request.addEventListener('error', function () {
			var statusCode = request.status;
			var statusText = request.statusText;
			var error = new Error(statusText);
			error.status = statusCode;
			_this.loadTrigger(error, request.response);
		});
		request.send();
	}

	// 支持 AMD 加载器
	if ( typeof define === "function" && define.amd ) {
		define( "preloader", [], function() {
			return preloader;
		});
	}

	return window.preloader = preloader;

})();/**
 * Created by 江杰爸爸 on 2016/7/25 0025.
 */
