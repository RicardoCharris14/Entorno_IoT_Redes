#include <iostream>
#include <fstream>
#include <ctime>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <thread>
#include <chrono>
#include <random>

int PORT = 8080;
std::string ADDR = "192.168.1.5";

std::random_device rd;
std::mt19937 gen(rd());

float generar_temperatura(){
    std::uniform_real_distribution<float> dis(0.0f, 30.0f);
    float valor = dis(gen);
    return std::round(valor * 10.0f) / 10.0f;
}

float generar_presion(){
    std::uniform_real_distribution<float> dis(0.70f, 1.30f);
    float valor = dis(gen);
    return std::round(valor * 100.0f) / 100.0f;
}

float generar_humedad(){
    std::uniform_real_distribution<float> dis(0.0f, 100.0f);
    float valor = dis(gen);
    return std::round(valor * 10.0f) / 10.0f;
}

// Convierte uint64_t a big-endian
uint64_t htonll(uint64_t value) {
    if (__BYTE_ORDER == __LITTLE_ENDIAN) {
        return (((uint64_t)htonl(value & 0xFFFFFFFF)) << 32) | htonl(value >> 32);
    } else {
        return value;
    }
}

// Convierte float a uint32_t big-endian
uint32_t float_to_network(float value) {
    uint32_t as_int;
    static_assert(sizeof(float) == sizeof(uint32_t), "float y uint32_t deben tener el mismo tamaño");
    std::memcpy(&as_int, &value, sizeof(float));
    return htonl(as_int);
}

int main(){
    
    while (true){

        int sock = socket(AF_INET, SOCK_STREAM, 0);
        sockaddr_in server{};
        server.sin_family = AF_INET;
        server.sin_port = htons(PORT);
        inet_pton(AF_INET, ADDR.c_str(), &server.sin_addr);

        if (connect(sock, (sockaddr*)&server, sizeof(server)) < 0){
            std::cerr << "Error al conectar con el servidor." << std::endl;
            close(sock);
            std::this_thread::sleep_for(std::chrono::seconds(5));
            continue;
        }

        std::ifstream input_file("id.txt");
        int id_from_file = 1;
        if (input_file.is_open()) {
            input_file >> id_from_file;
            input_file.close();
        }

        int16_t id = htons(id_from_file);
        uint64_t fecha_hora = htonll(time(nullptr));
        uint32_t temperatura = float_to_network(generar_temperatura());
        uint32_t presion = float_to_network(generar_presion());
        uint32_t humedad = float_to_network(generar_humedad());
    
        char buffer[22];
        memcpy(buffer, &id, 2);
        memcpy(buffer + 2, &fecha_hora, 8);
        memcpy(buffer + 10, &temperatura, 4);
        memcpy(buffer + 14, &presion, 4);
        memcpy(buffer + 18, &humedad, 4);
    
        ssize_t bytes_enviados = send(sock, buffer, sizeof(buffer), 0);
        if (bytes_enviados <= 0){
            std::cerr << "Error al enviar los datos." << std::endl;
        } else {
            std::cout << "Datos enviados correctamente." << std::endl;
        }

        std::ofstream output_file("id.txt");
        if (output_file){
            output_file << ++id_from_file;
            output_file.close();
        }
        

        close(sock);

        std::this_thread::sleep_for(std::chrono::seconds(5));
    }
    
    return 0;
}