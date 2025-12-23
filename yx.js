// ==UserScript==
// @name         MoviePilot 自动创建映射 & 商品 (URL传参版)
// @namespace    moviepilot.mapping
// @version      1.4
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
                    
                    console.log("拦截到API请求:", url);
                    console.log("API返回数据:", data);
                    
                    // 如果返回的是媒体数据
                    if(data && (data.title || data.name)) {
                        lastMediaData = {
                            title: data.title || data.name || data.original_title || data.original_name || "",
                            poster_path: data.poster_path || data.backdrop_path || "",
                            backdrop_path: data.backdrop_path || "",
                            category: data.category || ""
                        };
                        console.log("✓ 成功保存媒体数据:", lastMediaData);
                    }
                }
            } catch(e) {
                // 忽略非JSON响应
                console.log("拦截响应解析失败:", e);
            }
            
            return response;
        };

        // 从 localStorage 或 URL 获取媒体数据（备用）
        function fetchMediaData() {
            try{
                const urlParams = new URLSearchParams(location.hash.split("?")[1]);
                const mediaid = urlParams.get("mediaid");
                const titleParam = urlParams.get("title");
                if(!mediaid) return;

                const mediaStr = localStorage.getItem(`media_${mediaid}`);
                if(mediaStr){
                    const media = JSON.parse(mediaStr);
                    lastMediaData = {
                        title: media.title || media.name || decodeURIComponent(titleParam),
                        poster_path: media.poster_path || media.poster || "",
                        category: media.category || ""
                    };
                } else {
                    lastMediaData = {title: decodeURIComponent(titleParam), poster_path: "", category: ""};
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
                    // 移除所有按钮元素
                    clone.querySelectorAll('button').forEach(btn => btn.remove());
                    
                    const text = clone.textContent.trim();
                    // 排除网站名称和过滤无效文本
                    if(text && 
                       text !== 'MOVIEPILOT v2' && 
                       text !== 'MoviePilot' && 
                       !text.includes('创建映射') &&
                       !text.includes('创建商品') &&
                       text.length > 0){
                        // 清理多余的空格和换行
                        const cleanText = text.replace(/\s+/g, ' ').trim();
                        console.log(`找到标题(${selector}):`, cleanText);
                        return cleanText;
                    }
                }
            }
            
            console.log("未找到有效标题");
            return "";
        }

        // 创建按钮
        function createButtons(titleDom){
            if(document.getElementById("mp-create-map-btn")) return;

            fetchMediaData();
            
            // 优先从DOM获取数据，作为主要方案
            const domImage = getImageFromDOM();
            const domTitle = getTitleFromDOM();
            
            if(!lastMediaData || !lastMediaData.title){
                lastMediaData = {
                    title: domTitle,
                    poster_path: domImage,
                    category: ""
                };
            } else {
                // 补充缺失的图片
                if(!lastMediaData.poster_path && domImage){
                    lastMediaData.poster_path = domImage;
                }
                if(!lastMediaData.title && domTitle){
                    lastMediaData.title = domTitle;
                }
            }
            
            console.log("初始化数据:", lastMediaData);

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
                if(!lastMediaData){ alert("媒体数据未加载"); return; }
                GM_xmlhttpRequest({
                    method:"POST",
                    url:"http://10.10.10.17:9889/api/mappings",
                    headers:{"Content-Type":"application/json","Accept":"application/json"},
                    data:JSON.stringify({
                        id:null,
                        original_name:lastMediaData.title,
                        category:lastMediaData.category,
                        quark_name:lastMediaData.title,
                        baidu_name:lastMediaData.title,
                        xunlei_name:lastMediaData.title,
                        note:"",
                        enabled:true
                    }),
                    onload:()=>alert("映射创建成功！"),
                    onerror:(err)=>alert("请求失败："+err)
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
                
                // 标题：优先API，备用DOM
                if(lastMediaData && lastMediaData.title){
                    title = lastMediaData.title;
                    console.log("✓ 使用API标题:", title);
                } else {
                    title = domTitle;
                    console.log("✓ 使用DOM标题:", title);
                }
                
                // 图片：优先DOM，备用API
                if(domImage){
                    imageUrl = domImage;
                    console.log("✓ 使用DOM图片:", imageUrl);
                } else if(lastMediaData && (lastMediaData.poster_path || lastMediaData.backdrop_path)){
                    imageUrl = lastMediaData.poster_path || lastMediaData.backdrop_path;
                    console.log("✓ 使用API图片:", imageUrl);
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