

from spike.llm_conversation import llm_reply


def test_llm_reply():
    image_description = "题目描述: 这是一份四年级数学限时练习题的照片，图片中一共有5道数学题，分别为： 1. $2024\times2025\div} 111+2024\times65+37+6.28=$_____ 2. 有4、5、6、7、8克的砝码各1个，丢失了其中一个砝码，结果天平无法称出19克的质量(砝码必须放在天平的同一侧)。则丢失的砝码是_____克。 3. 20只质量相同的猫一组，18只质量相同的狗一组，两组共112千克，如果从两组中分别取8只猫与8只狗相交换，两组质量就相同了，每只狗比猫多_____千克。 4. 李老师在家和学校之间往返，去的时候步行，回来的时候骑车，共需要43分钟；如果小明往返都是骑车，则只需要15分钟。其中步行的速度保持一致，骑车的速度也保持一致。那么如果小明往返都是步行，需要_____分钟。 5. 如图所示的阴影部分是一枚手里剑的图形。已知点A、B、C、D、M、N、K、L都是相应的大正方形边上的中点，图中最小的正方形ABCD的边长是4厘米，那么这枚手里剑的面积是_____平方厘米。"
    stream_response = llm_reply("第3题不会", image_description)
    for chunk in stream_response:
        print(chunk)


if __name__ == "__main__":
    test_llm_reply()