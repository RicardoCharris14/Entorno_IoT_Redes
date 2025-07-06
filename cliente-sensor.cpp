#include <iostream>
#include <ctime>
#include <arpa/inet.h>
#include <unistd.h>

int PORT = 8080;
std::string ADDR = "127.0.0.1";

#pragma pack(1)
struct DatosSensor{
    int16_t id;
    time_t fecha_hora;
    float temperatura;
    float presion;
    float humedad;
};
#pragma pack()

int main(){
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in server{};
    server.sin_family = AF_INET;
    server.sin_port = htons(8080);
    inet_pton(AF_INET, ADDR.c_str(), &server.sin_addr);

    connect(sock, (sockaddr*)&server, sizeof(server));

    DatosSensor datos = {2, time(nullptr), 23.5, 1.02, 50.0};
    std::cout << sizeof(datos) << std::endl;
    send(sock, &datos, sizeof(datos), 0);

    close(sock);
    return 0;
}