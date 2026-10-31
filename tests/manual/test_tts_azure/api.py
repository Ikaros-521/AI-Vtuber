import azure.cognitiveservices.speech as speechsdk

def azure_tts_api(data):
    # 使用你的Azure认知服务订阅密钥和区域
    subscription_key = ""
    service_region = "japanwest"

    # file_name = 'azure_tts_' + self.common.get_bj_time(4) + '.wav'
    # voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
    voice_tmp_path = 'azure_tts_0.wav'
    
    # 创建语音配置对象，使用Azure订阅密钥和服务区域
    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=service_region)
    speech_config.speech_synthesis_voice_name = "zh-CN-liaoning-XiaobeiNeural"

    # 创建音频配置对象，指定输出音频文件路径
    audio_config = speechsdk.audio.AudioOutputConfig(filename=voice_tmp_path)

    # 创建语音合成器对象
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    # 执行文本到语音的转换
    result = speech_synthesizer.speak_text_async(data["content"]).get()

    # 检查结果
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"音频已成功保存到: {voice_tmp_path}")
        return voice_tmp_path
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"文本转语音取消: {str(cancellation_details.reason)}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print(f"错误详情: {str(cancellation_details.error_details)}")

        return None

# 要转换的文本
data = {
    "content": "你好"
}


# 调用函数
print(azure_tts_api(data))
