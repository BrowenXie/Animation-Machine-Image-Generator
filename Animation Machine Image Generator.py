#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手搖動畫機圖片生成器
從影片中提取畫面並進行錯位組合，製作手搖動畫效果
"""

import cv2
import os
from PIL import Image, ImageDraw, ImageFont
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading


class FlipbookGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("手搖動畫機生成器")
        self.root.geometry("600x550")
        self.root.resizable(False, False)
        
        # 變數初始化
        self.video_path = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.interval_seconds = tk.DoubleVar(value=0.1)
        self.image_width = tk.IntVar(value=800)
        self.font_size = tk.IntVar(value=40)
        self.split_position = tk.DoubleVar(value=0.5)
        self.add_border = tk.BooleanVar(value=True)
        self.processing = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # 標題
        title_label = tk.Label(
            self.root, 
            text="手搖動畫機圖片生成器", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 選擇影片
        video_frame = ttk.LabelFrame(main_frame, text="1. 選擇影片檔案", padding="10")
        video_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(video_frame, textvariable=self.video_path, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(video_frame, text="瀏覽", command=self.select_video).pack(side=tk.LEFT)
        
        # 2. 選擇輸出資料夾
        output_frame = ttk.LabelFrame(main_frame, text="2. 選擇輸出資料夾", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(output_frame, textvariable=self.output_folder, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(output_frame, text="瀏覽", command=self.select_output).pack(side=tk.LEFT)
        
        # 3. 參數設定
        params_frame = ttk.LabelFrame(main_frame, text="3. 參數設定", padding="10")
        params_frame.pack(fill=tk.X, pady=5)
        
        # 截圖間隔
        interval_frame = ttk.Frame(params_frame)
        interval_frame.pack(fill=tk.X, pady=3)
        ttk.Label(interval_frame, text="截圖間隔（秒）:", width=20).pack(side=tk.LEFT)
        ttk.Spinbox(
            interval_frame, 
            from_=0.01, 
            to=5.0, 
            increment=0.05,
            textvariable=self.interval_seconds,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        ttk.Label(interval_frame, text="（建議 0.05-0.2 秒）").pack(side=tk.LEFT)
        
        # 圖片寬度
        width_frame = ttk.Frame(params_frame)
        width_frame.pack(fill=tk.X, pady=3)
        ttk.Label(width_frame, text="輸出圖片寬度（px）:", width=20).pack(side=tk.LEFT)
        ttk.Spinbox(
            width_frame, 
            from_=400, 
            to=2000, 
            increment=100,
            textvariable=self.image_width,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # 切割位置
        split_frame = ttk.Frame(params_frame)
        split_frame.pack(fill=tk.X, pady=3)
        ttk.Label(split_frame, text="切割位置（0.5=中間）:", width=20).pack(side=tk.LEFT)
        ttk.Spinbox(
            split_frame, 
            from_=0.3, 
            to=0.7, 
            increment=0.05,
            textvariable=self.split_position,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # 數字字體大小
        font_frame = ttk.Frame(params_frame)
        font_frame.pack(fill=tk.X, pady=3)
        ttk.Label(font_frame, text="數字字體大小:", width=20).pack(side=tk.LEFT)
        ttk.Spinbox(
            font_frame, 
            from_=20, 
            to=100, 
            increment=5,
            textvariable=self.font_size,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # 選項
        options_frame = ttk.Frame(params_frame)
        options_frame.pack(fill=tk.X, pady=3)
        ttk.Checkbutton(
            options_frame, 
            text="添加圖片邊框", 
            variable=self.add_border
        ).pack(side=tk.LEFT, padx=20)
        
        # 進度條
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X)
        
        self.status_label = ttk.Label(progress_frame, text="就緒", foreground="green")
        self.status_label.pack(pady=5)
        
        # 按鈕
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        self.generate_button = ttk.Button(
            button_frame, 
            text="開始生成", 
            command=self.start_generation,
            width=20
        )
        self.generate_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="關於", 
            command=self.show_about,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
    def select_video(self):
        filename = filedialog.askopenfilename(
            title="選擇影片檔案",
            filetypes=[
                ("影片檔案", "*.mp4 *.avi *.mov *.mkv *.flv"),
                ("所有檔案", "*.*")
            ]
        )
        if filename:
            self.video_path.set(filename)
            # 自動設置輸出資料夾
            if not self.output_folder.get():
                video_dir = os.path.dirname(filename)
                video_name = Path(filename).stem
                output_dir = os.path.join(video_dir, f"{video_name}_flipbook")
                self.output_folder.set(output_dir)
    
    def select_output(self):
        folder = filedialog.askdirectory(title="選擇輸出資料夾")
        if folder:
            self.output_folder.set(folder)
    
    def show_about(self):
        about_text = """手搖動畫機生成器 v1.0
        
功能說明：
1. 從影片中按時間間隔提取畫面
2. 將圖片切割成上下兩半
3. 進行錯位組合（第N張下半+第N+1張上半）
4. 在底部添加序號數字
5. 輸出可用於製作手搖動畫的圖片

使用方法：
將生成的圖片依序排列，快速翻動即可看到動畫效果！
        """
        messagebox.showinfo("關於", about_text)
    
    def start_generation(self):
        if self.processing:
            messagebox.showwarning("警告", "正在處理中，請稍候...")
            return
            
        if not self.video_path.get():
            messagebox.showerror("錯誤", "請選擇影片檔案！")
            return
        
        if not self.output_folder.get():
            messagebox.showerror("錯誤", "請選擇輸出資料夾！")
            return
        
        # 在新線程中執行以避免界面凍結
        thread = threading.Thread(target=self.generate_flipbook)
        thread.daemon = True
        thread.start()
    
    def generate_flipbook(self):
        self.processing = True
        self.generate_button.config(state='disabled')
        self.progress.start()
        self.status_label.config(text="處理中...", foreground="blue")
        
        try:
            # 創建輸出資料夾
            output_dir = self.output_folder.get()
            os.makedirs(output_dir, exist_ok=True)
            
            # 步驟1: 提取影片幀
            self.update_status("步驟 1/3: 提取影片畫面...")
            frames = self.extract_frames()
            
            if len(frames) < 2:
                raise Exception("提取的畫面數量不足（至少需要2張）")
            
            # 步驟2: 切割和組合圖片
            self.update_status(f"步驟 2/3: 處理 {len(frames)} 張圖片...")
            combined_images = self.combine_frames(frames)
            
            # 步驟3: 添加數字並保存
            self.update_status(f"步驟 3/3: 保存 {len(combined_images)} 張圖片...")
            self.save_images(combined_images, output_dir)
            
            self.update_status(f"完成！共生成 {len(combined_images)} 張圖片", "green")
            messagebox.showinfo(
                "完成", 
                f"成功生成 {len(combined_images)} 張手搖動畫圖片！\n"
                f"保存位置：{output_dir}"
            )
            
        except Exception as e:
            self.update_status(f"錯誤：{str(e)}", "red")
            messagebox.showerror("錯誤", f"處理失敗：{str(e)}")
        
        finally:
            self.processing = False
            self.progress.stop()
            self.generate_button.config(state='normal')
    
    def update_status(self, text, color="blue"):
        self.status_label.config(text=text, foreground=color)
        self.root.update()
    
    def extract_frames(self):
        """從影片中提取畫面"""
        video_path = self.video_path.get()
        interval = self.interval_seconds.get()
        target_width = self.image_width.get()
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * interval)
        
        frames = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                # 調整大小
                height, width = frame.shape[:2]
                aspect_ratio = height / width
                new_height = int(target_width * aspect_ratio)
                
                resized = cv2.resize(frame, (target_width, new_height))
                # BGR to RGB
                rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                frames.append(pil_image)
            
            frame_count += 1
        
        cap.release()
        return frames
    
    def combine_frames(self, frames):
        """將圖片進行錯位組合"""
        split_ratio = self.split_position.get()
        combined = []
        
        for i in range(len(frames) - 1):
            img1 = frames[i]
            img2 = frames[i + 1]
            
            width, height = img1.size
            split_point = int(height * split_ratio)
            
            # 創建新圖片
            new_img = Image.new('RGB', (width, height))
            
            # 第i張的下半部
            bottom_part = img1.crop((0, split_point, width, height))
            new_img.paste(bottom_part, (0, split_point))
            
            # 第i+1張的上半部
            top_part = img2.crop((0, 0, width, split_point))
            new_img.paste(top_part, (0, 0))
            
            combined.append(new_img)
        
        # 添加最後一張（完整的）
        combined.append(frames[-1])
        
        return combined
    
    def save_images(self, images, output_dir):
        """保存圖片並添加數字標記"""
        font_size = self.font_size.get()
        add_border = self.add_border.get()
        
        # 嘗試使用系統字體
        try:
            # Windows
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                # Linux
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                # 使用默認字體
                font = ImageFont.load_default()
        
        for i, img in enumerate(images, 1):
            # 創建帶數字的圖片
            width, height = img.size
            number_height = font_size + 20
            
            # 創建新畫布（原圖 + 數字區域）
            final_img = Image.new('RGB', (width, height + number_height), 'white')
            final_img.paste(img, (0, 0))
            
            # 繪製數字
            draw = ImageDraw.Draw(final_img)
            text = str(i)
            
            # 計算文字位置（置中）
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            text_y = height + 10
            
            draw.text((text_x, text_y), text, fill='black', font=font)
            
            # 添加邊框
            if add_border:
                draw.rectangle(
                    [(0, 0), (width-1, height + number_height-1)], 
                    outline='black', 
                    width=2
                )
            
            # 保存
            filename = os.path.join(output_dir, f"frame_{i:04d}.png")
            final_img.save(filename, 'PNG')


def main():
    root = tk.Tk()
    app = FlipbookGenerator(root)
    root.mainloop()


if __name__ == "__main__":
    main()