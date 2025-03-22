# RAW Image Processing application
To run the RAW Image processor application on your computer without using the exe:
1. Clone this resposity in your desired directory
2. Get a google studio api key for gemini and create a .env file in the project folder and paste the below code with your api key and save the file:
```GOOGLE_AI_STUDIO_API_KEY = "yourAPIkey"```
3. You will need to have python installed at least version 3.12, make sure you are in the project folder and pip install the needed libraries using the command below (recommended to use a virtual enviroment):<br />
   ```pip install -r requirements. txt```
4. Now enter the image processor folder:<br />
   ```cd imageprocessor```
5. Now run the application:<br />
```flet run``` or ```flet run main.py```

The application accepts raw image files only and exports them as jpeg, use the images in the sample images folder to test it out for yourself.

To run the tests simply run ```pytest``` in your terminal from your folder containing the project, you will need to ```pip install pytest```. 

link to uml: https://drive.google.com/file/d/1LToHPn-f3IeUVpPsEWQXLye6E9LZXuPK/view?usp=sharing
