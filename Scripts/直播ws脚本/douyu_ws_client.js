let socket = null;

function connectWebSocket() {
  // 创建 WebSocket 连接，适配服务端
  socket = new WebSocket("ws://127.0.0.1:5001");

  // 当连接建立时触发
  socket.addEventListener("open", event => {
    console.log("ws连接打开");

    // 向服务器发送一条消息
    // socket.send("ws连接成功");
  });

  // 当收到消息时触发
  socket.addEventListener("message", event => {
    console.log("收到服务器数据:", event.data);
  });

  // 当连接关闭时触发
  socket.addEventListener("close", event => {
    console.log("WS连接关闭");

    // 重连
    setTimeout(() => {
      connectWebSocket();
    }, 1000); // 延迟 1 秒后重连
  });
}

// 初始连接
connectWebSocket();


// 选择需要观察变化的节点
const targetNode = document.querySelector('.Barrage-list');

// 创建观察器实例
const observer = new MutationObserver(mutations => {
  mutations.forEach(mutation => {
    // 这里处理新增的DOM元素
    if (mutation.type === 'childList') {
      mutation.addedNodes.forEach(node => {
        // 判断是否是新增的弹幕消息
        if (node.classList.contains('Barrage-listItem')) {
          // 新增的动态DOM元素处理
          // console.log('Added node:', node);

          const spans = node.getElementsByTagName('span');

          let username = "";
          let content = "";

          for (let span of spans) {
            //console.log(span);
            if (span.classList.contains('Barrage-nickName')) {
              const targetSpan = span;
              // 获取用户名
              let tmp = targetSpan.textContent.trim().slice(0, -1);
              if (tmp != "") username = targetSpan.textContent.trim().slice(0, -1);
            } else if (span.classList.contains('Barrage-content')) {
              const targetSpan = span;
              // 获取弹幕内容
              content = targetSpan.textContent.trim();
            }
          }

          console.log(username + ":" + content);

          // 获取到弹幕数据
          if (username != "" && content != "") {
            const data = {
              type: "comment",
              username: username,
              content: content
            };
            console.log(data);
            socket.send(JSON.stringify(data));
          }
        }
      })
    }
  });
});

// 配置观察选项
const config = {
  childList: true,
  subtree: true
};

// 开始观察
observer.observe(targetNode, config);