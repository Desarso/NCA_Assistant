import { useCallback, useEffect, useState } from "@lynx-js/react";

import "./App.css";
import Chatbox from "./aichat/pages/Chatbox.jsx";

export function App() {
  const [alterLogo, setAlterLogo] = useState(false);

  useEffect(() => {
    console.info("Hello, ReactLynx");
  }, []);

  const onTap = useCallback(() => {
    "background only";
    setAlterLogo(!alterLogo);
  }, [alterLogo]);

  return (
    <view>
      <view className="Background" />
      <view className="App">
        {/* <view className='Banner'>
          <view className='Logo' bindtap={onTap}>
            {alterLogo
              ? <image src={reactLynxLogo} className='Logo--react' />
              : <image src={lynxLogo} className='Logo--lynx' />}
          </view>
          <text className='Title'>React</text>
          <text className='Subtitle'>on Lynx</text>
        </view> */}
        <view className="Content">
          <Chatbox />
        </view>
        <view style={{ flex: 1 }}></view>
      </view>
    </view>
  );
}
