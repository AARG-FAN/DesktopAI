##  General Info
- 20241012update：1.修复聊天界面滑杆问题 2.增加休眠与唤醒功能 3.修补部分bug   

![image](https://github.com/user-attachments/assets/e76e8345-024d-480f-9724-0909c915c9b2)    
![image](https://github.com/user-attachments/assets/46556276-46cb-4abe-98aa-5c766e631e51)    


##  General Info
- This project is a framework for desktop AI assistant based on sensevoice: https://github.com/FunAudioLLM/SenseVoice , BigModel platform: https://bigmodel.cn/ , Volcano Engine: https://www.volcengine.com/ 
- please check this link for more info and api docs

##  Installation   
Tutorial Video: 
https://www.bilibili.com/video/BV1eY2VYDEH6/   

   
- 1.下载miniconda/anaconda（如有请忽略）  
https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe   
- 2.下载C++Make Tools（靠这个编译c++,如有Visual Studio请忽略）   
https://aka.ms/vs/17/release/vs_BuildTools.exe   
- 3.Conda中创建虚拟环境：  
  conda create -n desktopai python==3.8.19  
  conda  activate desktopai  
- 4.下载代码：  
cd /d “your dir”  (导航到安装根文件夹)    
git clone https://github.com/AARG-FAN/DesktopAI.git  
- 5.cd /d DesktopAI  (导航到项目的文件夹)    
- 6.安装依赖：  
pip install -r requirements.txt  
- 7.启动：  
python main.py  

##  Tips
- 1.按空格键可以跳过当前语音播放  
- 2.右键休眠可以让他休眠不再处理文字。右键可以选择设置特定词语作为唤醒词，休眠后检测到特定词语后会唤醒AI  
- 3.更换角色形象可以在文件夹assest中的role1和role2文件夹中同名替换gif1（静止）和gif2（说话）文件即可   

  
##  Attention
- 安装成功后启动项目时候不要用vpn，因为api服务商在国内，vpn影响通信

##  Function Introduction
- Adding...

## Star History
[![Star History Chart](https://api.star-history.com/svg?repos=AARG-FAN/DesktopAI&type=Date)](https://star-history.com/#AARG-FAN/DesktopAI&Date)



