// ==UserScript==
// @name         MoviePilot 自动创建映射 & 商品 (URL传参版)
// @namespace    moviepilot.mapping
// @version      1.5
// @description  SPA 页面自动插入按钮并跳转商品页面，带标题和封面图
// @match        http://10.10.10.17:3000/*
// @match        http://localhost:8888/*
// @grant        GM_xmlhttpRequest
// @connect      10.10.10.17
// ==/UserScript==

(function() {

    const isMP = location.hostname === "10.10.10.17" && location.port === "3000";
    const isProductPage = location.hostname === "xy.naspt.vip" ;

    if(isMP){

        let lastMediaData = null;

        // 拦截 XMLHttpRequest
        console.log("✅ XHR拦截器已设置");
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalXHRSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(method, url, ...args) {
            this._url = url;
            console.log("🌐 XHR.open被调用:", url);
            return originalXHROpen.apply(this, [method, url, ...args]);
        };
        
        XMLHttpRequest.prototype.send = function(...args) {
            this.addEventListener('load', function() {
                if(this._url && (this._url.includes('/api/v1/media/') || this._url.includes('api/v1/media/'))) {
                    try {
                        const data = JSON.parse(this.responseText);
                        
                        console.log("🔍========== XHR拦截 ==========");
                        console.log("URL:", this._url);
                        console.log("📦 完整API返回数据:", JSON.stringify(data, null, 2));
                        console.log("📦 API数据的所有字段名:", Object.keys(data));
                        
                        const hasValidTitle = data.title_year || (data.title && data.year);
                        
                        console.log("🔍 数据检查:");
                        console.log("  ├─ hasValidTitle:", hasValidTitle);
                        console.log("  ├─ data.title_year:", data.title_year);
                        console.log("  ├─ data.title:", data.title);
                        console.log("  ├─ data.year:", data.year);
                        console.log("  ├─ data.type:", data.type);
                        console.log("  ├─ data.category:", data.category);
                        
                        if(hasValidTitle) {
                            // 保存两个版本：title_year（含年份）和 title（不含年份）
                            let titleWithYear = data.title_year;
                            if(!titleWithYear && data.title && data.year){
                                titleWithYear = `${data.title} (${data.year})`;
                                console.log("  ✅ 拼接标题:", titleWithYear);
                            }
                            
                            // 不含年份的标题
                            const titleWithoutYear = data.title || "";
                            
                            // 优先使用category字段（如"电影/国产电影"），其次才用type
                            let finalCategory = data.category || data.type || "";
                            console.log("  📝 最终category:", finalCategory);
                            
                            // 如果还是空，保留旧值
                            const savedCategory = finalCategory || lastMediaData?.category || "";
                            
                            lastMediaData = {
                                title: titleWithoutYear,           // 不含年份
                                title_year: titleWithYear,         // 含年份
                                poster_path: data.poster_path || data.backdrop_path || "",
                                backdrop_path: data.backdrop_path || "",
                                category: savedCategory
                            };
                            
                            console.log("✅ XHR拦截保存:");
                            console.log("  ├─ title:", lastMediaData.title);
                            console.log("  ├─ title_year:", lastMediaData.title_year);
                            console.log("  └─ category:", lastMediaData.category);
                        }
                        console.log("🔍================================");
                    } catch(e) {
                        console.log("XHR响应解析失败:", e);
                    }
                }
            });
            return originalXHRSend.apply(this, args);
        };

        // 拦截 Fetch API 获取媒体数据
        const originalFetch = window.fetch;
        window.fetch = async function(...args) {
            const response = await originalFetch.apply(this, args);
            
            // 克隆响应以便读取
            const clonedResponse = response.clone();
            
            try {
                const url = args[0];
                // 检查是否是媒体详情API
                if(url && url.includes('/api/v1/media/')) {
                    const data = await clonedResponse.json();
                    
                    console.log("🔍========== API拦截 ==========");
                    console.log("URL:", url);
                    console.log("📦 完整API返回数据:", JSON.stringify(data, null, 2));
                    console.log("📦 API数据的所有字段名:", Object.keys(data));
                    
                    // 判断是否为完整的详情数据
                    const hasValidTitle = data.title_year || (data.title && data.year);
                    
                    console.log("🔍 数据检查:");
                    console.log("  ├─ hasValidTitle:", hasValidTitle);
                    console.log("  ├─ data.title_year:", data.title_year);
                    console.log("  ├─ data.title:", data.title);
                    console.log("  ├─ data.year:", data.year);
                    console.log("  ├─ data.type:", data.type);
                    console.log("  ├─ data.category:", data.category);
                    console.log("  └─ URL包含type_name:", url.includes('type_name='));
                    
                    if(hasValidTitle) {
                        // 优先使用 title_year
                        let finalTitle = data.title_year;
                        if(!finalTitle && data.title && data.year){
                            finalTitle = `${data.title} (${data.year})`;
                            console.log("  ✅ 拼接标题:", finalTitle);
                        }
                        
                        // 获取category，如果API返回为空，尝试从URL参数提取
                        let finalCategory = data.category || "";
                        console.log("  📝 初始category:", finalCategory);
                        console.log("  📝 !finalCategory:", !finalCategory);
                        
                        if(!finalCategory && url.includes('type_name=')) {
                            console.log("  🔄 尝试从URL提取category...");
                            try {
                                // 构建完整URL（如果url是相对路径）
                                const fullUrl = url.startsWith('http') ? url : `http://10.10.10.17:3000${url}`;
                                console.log("  📋 完整URL:", fullUrl);
                                const urlObj = new URL(fullUrl);
                                const typeName = urlObj.searchParams.get('type_name');
                                console.log("  📋 type_name参数:", typeName);
                                if(typeName) {
                                    // URL参数是编码的，需要解码
                                    finalCategory = decodeURIComponent(typeName);
                                    console.log("  ✅ 从URL参数提取category:", finalCategory);
                                }
                            } catch(e) {
                                console.log("  ⚠️ 解析URL失败:", e);
                            }
                        }
                        
                        // 如果category还是空，保留旧值
                        if(!finalCategory && lastMediaData?.category) {
                            finalCategory = lastMediaData.category;
                            console.log("  📝 使用旧category:", finalCategory);
                        }
                        
                        // 保存数据：如果新数据的category为空但旧数据有值，则保留旧的category
                        const savedCategory = finalCategory || lastMediaData?.category || "";
                        
                        lastMediaData = {
                            title: finalTitle,
                            poster_path: data.poster_path || data.backdrop_path || "",
                            backdrop_path: data.backdrop_path || "",
                            category: savedCategory
                        };
                        
                        console.log("  💾 实际保存的category:", savedCategory);
                        
                        console.log("✅ 最终保存:");
                        console.log("  ├─ title:", lastMediaData.title);
                        console.log("  └─ category:", lastMediaData.category);
                    } else {
                        console.log("⚠️ 数据不完整，跳过");
                    }
                    console.log("🔍================================");
                }
            } catch(e) {
                // 忽略非JSON响应
                console.log("拦截响应解析失败:", e);
            }
            
            return response;
        };

        // 从 localStorage 或 URL 获取媒体数据（备用）
        function fetchMediaData() {
            // 如果API已经拦截到数据，不要覆盖
            if(lastMediaData && lastMediaData.title){
                console.log("⚠️ API数据已存在，跳过localStorage读取");
                return;
            }
            
            try{
                const urlParams = new URLSearchParams(location.hash.split("?")[1]);
                const mediaid = urlParams.get("mediaid");
                const titleParam = urlParams.get("title");
                if(!mediaid) return;

                const mediaStr = localStorage.getItem(`media_${mediaid}`);
                if(mediaStr){
                    const media = JSON.parse(mediaStr);
                    lastMediaData = {
                        title: media.title_year || media.name || decodeURIComponent(titleParam),
                        poster_path: media.poster_path || media.poster || "",
                        category: media.category || ""
                    };
                    console.log("📦 从localStorage读取数据:", lastMediaData);
                } else {
                    lastMediaData = {title: decodeURIComponent(titleParam), poster_path: "", category: ""};
                    console.log("🔗 从URL参数读取数据:", lastMediaData);
                }
            } catch(e){ console.error(e); }
        }

        // 从页面DOM获取图片
        function getImageFromDOM(){
            const allImages = document.querySelectorAll('img');
            console.log(`页面共有 ${allImages.length} 张图片`);
            
            let foundImages = [];
            
            // 收集所有可能的图片
            for(const img of allImages){
                if(img.src && img.src.includes('http')){
                    foundImages.push({
                        src: img.src,
                        width: img.naturalWidth || img.width,
                        height: img.naturalHeight || img.height,
                        alt: img.alt || '',
                        className: img.className || ''
                    });
                }
            }
            
            console.log("找到的图片:", foundImages);
            
            // 优先级1: 包含 tmdb 或 cache/image 的
            for(const img of foundImages){
                if(img.src.includes('image.tmdb') || img.src.includes('cache/image')){
                    console.log("✓ 找到TMDB/缓存图片:", img.src);
                    return img.src;
                }
            }
            
            // 优先级2: 尺寸最大的图片（通常是海报）
            if(foundImages.length > 0){
                foundImages.sort((a, b) => (b.width * b.height) - (a.width * a.height));
                console.log("✓ 使用最大尺寸图片:", foundImages[0].src);
                return foundImages[0].src;
            }
            
            console.log("✗ 未找到任何图片");
            return "";
        }

        // 从页面获取标题
        function getTitleFromDOM(){
            // 尝试多种选择器
            const selectors = [
                '.media-title',
                '.title',
                'h1.text-2xl',
                'h1',
                'h2.media-name',
                'h2',
                '[class*="title"]'
            ];
            
            for(const selector of selectors){
                const el = document.querySelector(selector);
                if(el){
                    // 克隆元素以避免修改原DOM
                    const clone = el.cloneNode(true);
                    // 移除所有按钮元素（保留标题和年份的div）
                    clone.querySelectorAll('button').forEach(btn => btn.remove());
                    
                    const text = clone.textContent.trim();
                    // 排除网站名称和过滤无效文本
                    if(text && 
                       text !== 'MOVIEPILOT v2' && 
                       text !== 'MoviePilot' && 
                       !text.includes('创建映射') &&
                       !text.includes('创建商品') &&
                       text.length > 0){
                        // 清理多余的空格和换行，规范化年份格式
                        let cleanText = text.replace(/\s+/g, ' ').trim();
                        // 统一年份括号为英文括号
                        cleanText = cleanText.replace(/（(\d{4})）/g, '($1)');
                        // 移除时长和多余的分隔符（如"99 分钟 |"）
                        cleanText = cleanText.replace(/\s+\d+\s*分钟.*$/g, '');
                        cleanText = cleanText.replace(/\s*\|+\s*$/g, '');
                        console.log(`✓ 找到标题(${selector}):`, cleanText);
                        return cleanText;
                    }
                }
            }
            
            console.log("✗ 未找到有效标题");
            return "";
        }

        // 创建按钮
        function createButtons(titleDom){
            if(document.getElementById("mp-create-map-btn")) return;

            console.log("🔍 ========== 按钮创建开始 ==========");
            console.log("当前 lastMediaData:", JSON.stringify(lastMediaData, null, 2));
            
            fetchMediaData();
            
            console.log("fetchMediaData后 lastMediaData:", JSON.stringify(lastMediaData, null, 2));
            
            // 从DOM获取数据作为备用
            const domImage = getImageFromDOM();
            const domTitle = getTitleFromDOM();
            
            console.log("🔍 数据源对比:");
            console.log("  - API拦截数据存在:", !!lastMediaData);
            console.log("  - API.title:", lastMediaData?.title);
            console.log("  - API.category:", lastMediaData?.category);
            console.log("  - DOM.title:", domTitle);
            
            // 优先使用API数据，DOM数据只作为备用
            if(!lastMediaData || !lastMediaData.title){
                console.log("⚠️ 使用DOM数据（API数据缺失）");
                lastMediaData = {
                    title: domTitle,
                    poster_path: domImage,
                    category: ""
                };
            } else {
                console.log("✓ 使用API拦截数据");
                // 只补充缺失的图片，不要用DOM覆盖title
                if(!lastMediaData.poster_path && domImage){
                    lastMediaData.poster_path = domImage;
                }
            }
            
            console.log("📋 最终使用数据:", JSON.stringify(lastMediaData, null, 2));
            console.log("� ========== 按钮创建结束 ==========");

            // 创建按钮容器
            const btnContainer = document.createElement("span");
            btnContainer.style.display = "inline-flex";
            btnContainer.style.gap = "8px";
            btnContainer.style.marginLeft = "12px";

            const btnStyle = {
                padding:"4px 10px",fontSize:"12px",fontWeight:"500",
                backgroundColor:"#007bff",color:"#fff",border:"none",borderRadius:"4px",cursor:"pointer",transition:"0.2s"
            };

            // --- 创建映射按钮 ---
            const btnMap = document.createElement("button");
            btnMap.id = "mp-create-map-btn";
            btnMap.innerText = "创建映射";
            Object.assign(btnMap.style, btnStyle);
            btnMap.onmouseenter = ()=>btnMap.style.backgroundColor="#0056b3";
            btnMap.onmouseleave = ()=>btnMap.style.backgroundColor="#007bff";
            btnMap.onclick = () => {
                // 优先使用API拦截的数据（title_year和category）
                // 如果API数据不存在，才用DOM作为备用
                const finalTitle = lastMediaData?.title_year || getTitleFromDOM() || "";
                const finalCategory = lastMediaData?.category || "";
                
                console.log("📤 创建映射 - 使用数据:", {
                    "来源": lastMediaData?.title ? "API拦截" : "DOM",
                    "original_name": finalTitle,
                    "category": finalCategory,
                    "完整API数据": lastMediaData
                });
                
                if(!finalTitle){
                    alert("无法获取标题");
                    return;
                }
                
                if(!finalCategory){
                    console.warn("⚠️ 警告: category为空，API可能未拦截到数据");
                }
                
                // 先调用混淆API检查是否已存在
                console.log("🔄 调用混淆API...");
                GM_xmlhttpRequest({
                    method:"POST",
                    url:`http://10.10.10.17:9889/api/mappings/obfuscate?original_name=${encodeURIComponent(finalTitle)}`,
                    headers:{"Content-Type":"application/x-www-form-urlencoded","Accept":"application/json"},
                    onload:(response) => {
                        try {
                            const result = JSON.parse(response.responseText);
                            console.log("📦 混淆API返回:", result);
                            
                            if(result.success && result.data) {
                                const obfuscatedName = result.data.obfuscated_name;
                                const isExisting = result.data.is_existing;
                                
                                console.log("  ├─ 混淆名称:", obfuscatedName);
                                console.log("  └─ 是否已存在:", isExisting);
                                
                                if(isExisting) {
                                    alert(`映射已存在：${obfuscatedName}`);
                                    return;
                                }
                                
                                // 使用混淆名称创建映射
                                const requestBody = {
                                    id:null,
                                    original_name: finalTitle,
                                    category: finalCategory,
                                    quark_name: obfuscatedName,
                                    baidu_name: obfuscatedName,
                                    xunlei_name: obfuscatedName,
                                    note:"",
                                    enabled:true
                                };
                                
                                console.log("📮 即将发送的完整请求体:", JSON.stringify(requestBody, null, 2));
                                console.log("📮 请求体中的所有字段:");
                                for(const [key, value] of Object.entries(requestBody)) {
                                    console.log(`  - ${key}: "${value}" (类型: ${typeof value})`);
                                }
                                
                                GM_xmlhttpRequest({
                                    method:"POST",
                                    url:"http://10.10.10.17:9889/api/mappings",
                                    headers:{"Content-Type":"application/json","Accept":"application/json"},
                                    data:JSON.stringify(requestBody),
                                    onload:()=>alert(`映射创建成功！\n混淆名称：${obfuscatedName}`),
                                    onerror:(err)=>alert("创建映射失败："+err)
                                });
                            } else {
                                alert("混淆API返回格式错误");
                            }
                        } catch(e) {
                            console.error("解析混淆API响应失败:", e);
                            alert("混淆API调用失败");
                        }
                    },
                    onerror:(err)=>{
                        console.error("混淆API请求失败:", err);
                        alert("混淆API请求失败："+err);
                    }
                });
            };

            // --- 创建商品按钮 ---
            const btnProduct = document.createElement("button");
            btnProduct.id = "mp-create-product-btn";
            btnProduct.innerText = "创建商品";
            Object.assign(btnProduct.style, btnStyle);
            btnProduct.onmouseenter = ()=>btnProduct.style.backgroundColor="#0056b3";
            btnProduct.onmouseleave = ()=>btnProduct.style.backgroundColor="#007bff";
            btnProduct.onclick = () => {
                console.log("=== 开始获取数据 ===");
                console.log("当前 lastMediaData:", lastMediaData);
                
                let title = "";
                let imageUrl = "";
                
                // 优先从DOM获取图片（因为DOM能获取到缓存URL）
                const domImage = getImageFromDOM();
                const domTitle = getTitleFromDOM();
                
                console.log("DOM获取结果 - 标题:", domTitle, "图片:", domImage);
                
                // 标题：优先API（不含年份），备用DOM
                if(lastMediaData && lastMediaData.title){
                    title = lastMediaData.title;  // 使用不含年份的title
                    console.log("✓ 使用API标题(不含年份):", title);
                } else {
                    title = domTitle;
                    console.log("✓ 使用DOM标题:", title);
                }
                
                // 图片：优先API的poster_path，备用DOM
                if(lastMediaData && (lastMediaData.poster_path || lastMediaData.backdrop_path)){
                    imageUrl = lastMediaData.poster_path || lastMediaData.backdrop_path;
                    console.log("✓ 使用API图片:", imageUrl);
                } else if(domImage){
                    imageUrl = domImage;
                    console.log("✓ 使用DOM图片:", imageUrl);
                } else {
                    console.warn("✗ 未找到任何图片源");
                }
                
                if(!imageUrl){
                    console.warn("警告: 图片URL为空！");
                }
                
                // 提取本地缓存URL中的实际图片地址
                if(imageUrl && imageUrl.includes('/cache/image?url=')){
                    console.log("检测到缓存URL，开始提取...");
                    try{
                        const urlObj = new URL(imageUrl);
                        const realUrl = urlObj.searchParams.get('url');
                        if(realUrl){
                            imageUrl = decodeURIComponent(realUrl);
                            console.log("✓ 提取成功:", imageUrl);
                        }
                    } catch(e){
                        console.error("✗ 解析缓存URL失败:", e);
                    }
                }
                
                // 处理相对路径
                if(imageUrl && !imageUrl.startsWith("http") && imageUrl.startsWith("/")){
                    const oldUrl = imageUrl;
                    imageUrl = `https://image.tmdb.org/t/p/w500${imageUrl}`;
                    console.log("拼接相对路径:", oldUrl, "=>", imageUrl);
                }

                console.log("=== 最终结果 ===");
                console.log("标题:", title);
                console.log("图片URL:", imageUrl);
                console.log("===============");

                if(!title){
                    alert("无法获取标题");
                    return;
                }

                // 生成带参数的 URL
                const url = new URL("https://xy.naspt.vip/index.html");
                url.searchParams.set("name", title);
                url.searchParams.set("image", imageUrl);
                
                console.log("跳转URL:", url.toString());
                window.open(url.toString(), "_blank");
            };

            btnContainer.appendChild(btnMap);
            btnContainer.appendChild(btnProduct);
            titleDom.appendChild(btnContainer);
        }

        // SPA 页面，使用 MutationObserver 监听 DOM
        const observer = new MutationObserver(mutations => {
            for(const m of mutations){
                const titleDom = document.querySelector(".title, .media-title");
                if(titleDom){
                    createButtons(titleDom);
                    break;
                }
            }
        });
        observer.observe(document.body, {childList:true, subtree:true});

        // 页面已渲染时立即插入
        const titleDom = document.querySelector(".title, .media-title");
        if(titleDom) createButtons(titleDom);

    } else if(isProductPage){

        // ----------------- 商品页面 ----------------- //

        const params = new URLSearchParams(window.location.search);
        const title = params.get("name");
        const poster = params.get("image");

        if(title){
            const titleDom = document.querySelector("#centerTitle");
            if(titleDom) titleDom.innerText = decodeURIComponent(title);
        }

        if(poster){
            const canvasDom = document.querySelector("#canvas");
            if(canvasDom){
                canvasDom.innerHTML = "";
                const img = document.createElement("img");
                img.src = decodeURIComponent(poster);
                img.style.maxWidth = "100%";
                canvasDom.appendChild(img);
            }
        }
    }

})();